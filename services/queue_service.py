from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from database.repositories import UserRepository, DutyRepository, WaterRepository


# Fixed Water Queue Sequence (User IDs 1..8)
# Index order: [Avazbek(1), Firdavs(2), Asadbek bro(3), Omadbek(4), Ilyosbek(5), Jaloliddin(6), Asadbek(7), Mavlonbek(8)]
WATER_QUEUE_IDS = [1, 2, 3, 4, 5, 6, 7, 8]

# Default Daily Duty Rotations (0=Mon, 1=Tue, ..., 6=Sun)
DEFAULT_DAILY_DUTY = {
    0: [6],       # Mon: Jaloliddin
    1: [2],       # Tue: Firdavs
    2: [7],       # Wed: Asadbek
    3: [3],       # Thu: Asadbek bro
    4: [8],       # Fri: Mavlonbek
    5: [1],       # Sat: Avazbek
    6: [4, 5]     # Sun: Omadbek & Ilyosbek
}

# Default Laundry Duty Rotations (0=Mon, 1=Tue, ..., 6=Sun)
DEFAULT_LAUNDRY_DUTY = {
    0: [2, 8],    # Mon: Firdavs / Mavlonbek
    1: [6],       # Tue: Jaloliddin
    2: [3],       # Wed: Asadbek bro
    3: [4],       # Thu: Omadbek
    4: [7],       # Fri: Asadbek
    5: [5],       # Sat: Ilyosbek
    6: [1, 8]     # Sun: Avazbek / Mavlonbek
}

# Weekly Deep Cleaning Pairs (Rotates by week_number % 4)
SUNDAY_CLEANING_PAIRS = [
    [4, 3],  # Pair 1: Omadbek & Asadbek bro
    [5, 6],  # Pair 2: Ilyosbek & Jaloliddin
    [1, 2],  # Pair 3: Avazbek & Firdavs
    [8, 7]   # Pair 4: Mavlonbek & Asadbek
]

DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]



class QueueService:
    @staticmethod
    async def get_daily_duty(target_date: date) -> List[Dict[str, Any]]:
        year, week_num, day_of_week = target_date.isocalendar()
        # day_of_week in isocalendar is 1..7 (Mon=1..Sun=7). Convert to 0..6 (Mon=0..Sun=6)
        day_idx = target_date.weekday()

        override_str = await DutyRepository.get_daily_override(week_num, day_idx)
        if override_str:
            user_ids = [int(x.strip()) for x in override_str.split(",") if x.strip()]
        else:
            user_ids = DEFAULT_DAILY_DUTY.get(day_idx, [])

        users = []
        for uid in user_ids:
            u = await UserRepository.get_user_by_id(uid)
            if u:
                users.append(u)
        return users

    @staticmethod
    async def get_laundry_duty(target_date: date) -> List[Dict[str, Any]]:
        day_idx = target_date.weekday()
        user_ids = DEFAULT_LAUNDRY_DUTY.get(day_idx, [])
        users = []
        for uid in user_ids:
            u = await UserRepository.get_user_by_id(uid)
            if u:
                users.append(u)
        return users

    @staticmethod
    async def get_water_duty_info() -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        curr_idx = await WaterRepository.get_current_water_index()
        curr_uid = WATER_QUEUE_IDS[curr_idx % 8]
        next_idx = (curr_idx + 1) % 8
        next_uid = WATER_QUEUE_IDS[next_idx]

        curr_user = await UserRepository.get_user_by_id(curr_uid)
        next_user = await UserRepository.get_user_by_id(next_uid)
        return curr_user, next_user, curr_idx

    @staticmethod
    async def record_water_delivery(brought_by_user_id: int, photo_file_id: str) -> Dict[str, Any]:
        now_str = datetime.now().isoformat()
        log_id = await WaterRepository.add_water_log(brought_by_user_id, photo_file_id, now_str)

        # Recalculate water queue starting from bringer
        if brought_by_user_id in WATER_QUEUE_IDS:
            bringer_idx = WATER_QUEUE_IDS.index(brought_by_user_id)
        else:
            bringer_idx = 0

        next_idx = (bringer_idx + 1) % 8
        await WaterRepository.set_current_water_index(next_idx)

        brought_user = await UserRepository.get_user_by_id(brought_by_user_id)
        next_user = await UserRepository.get_user_by_id(WATER_QUEUE_IDS[next_idx])

        return {
            "log_id": log_id,
            "brought_by": brought_user,
            "next_user": next_user,
            "next_index": next_idx
        }

    @staticmethod
    async def get_sunday_deep_clean_pair(target_date: date) -> List[Dict[str, Any]]:
        year, week_num, day_idx = target_date.isocalendar()
        pair_idx = week_num % 4
        pair_user_ids = SUNDAY_CLEANING_PAIRS[pair_idx]
        users = []
        for uid in pair_user_ids:
            u = await UserRepository.get_user_by_id(uid)
            if u:
                users.append(u)
        return users
