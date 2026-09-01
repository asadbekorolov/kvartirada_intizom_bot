from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from database.repositories import UserRepository, DutyRepository, WaterRepository


# Dual-Room Independent Water Queues (4 flatmates per room)
# Room 1: Avazbek (1), Firdavs (2), Asadbek bro (3), Omadbek (4)
ROOM_1_WATER_QUEUE = [1, 2, 3, 4]

# Room 2: Ilyosbek (5), Jaloliddin (6), Asadbek (7), Mavlonbek (8)
ROOM_2_WATER_QUEUE = [5, 6, 7, 8]

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

# Monthly 4-Week Rotating Pairs (for Deep Clean & Market Runs)
# Week 1 (Days 1..7): Pair 1 -> Omadbek (4) & Asadbek bro (3)
# Week 2 (Days 8..14): Pair 2 -> Ilyosbek (5) & Jaloliddin (6)
# Week 3 (Days 15..21): Pair 3 -> Avazbek (1) & Firdavs (2)
# Week 4 (Days 22..end): Pair 4 -> Mavlonbek (8) & Asadbek (7)
MONTHLY_DEFAULT_PAIRS = {
    0: (1, 4, 3),  # (Pair_ID, Member1_ID, Member2_ID)
    1: (2, 5, 6),
    2: (3, 1, 2),
    3: (4, 8, 7)
}

DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


class QueueService:
    @staticmethod
    def get_month_week_index(target_date: date) -> int:
        """
        Calculates week index of the month:
        - Days 1..7   -> 0 (Week 1)
        - Days 8..14  -> 1 (Week 2)
        - Days 15..21 -> 2 (Week 3)
        - Days 22..31 -> 3 (Week 4)
        """
        day = target_date.day
        week_idx = (day - 1) // 7
        return min(week_idx, 3)

    @staticmethod
    async def get_daily_duty(target_date: date) -> List[Dict[str, Any]]:
        year, week_num, _ = target_date.isocalendar()
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
    async def get_active_weekly_pair(target_date: date) -> Dict[str, Any]:
        """
        Returns active pair for Sunday Deep Clean & Weekly Market runs.
        """
        month_year = target_date.strftime("%Y-%m")
        week_idx = QueueService.get_month_week_index(target_date)

        override = await DutyRepository.get_weekly_pair_assignment(month_year, week_idx)
        if override:
            pair_id = override["pair_id"]
            m1_id = override["member1_id"]
            m2_id = override["member2_id"]
            is_overridden = True
        else:
            pair_id, m1_id, m2_id = MONTHLY_DEFAULT_PAIRS[week_idx]
            is_overridden = False

        m1 = await UserRepository.get_user_by_id(m1_id)
        m2 = await UserRepository.get_user_by_id(m2_id)

        return {
            "week_index": week_idx,
            "week_number_in_month": week_idx + 1,
            "pair_id": pair_id,
            "member1": m1,
            "member2": m2,
            "is_overridden": is_overridden,
            "month_year": month_year
        }

    @staticmethod
    async def get_room_water_duty_info(room_id: int) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        queue_ids = ROOM_1_WATER_QUEUE if room_id == 1 else ROOM_2_WATER_QUEUE
        curr_idx = await WaterRepository.get_room_water_index(room_id)
        curr_uid = queue_ids[curr_idx % len(queue_ids)]
        next_idx = (curr_idx + 1) % len(queue_ids)
        next_uid = queue_ids[next_idx]

        curr_user = await UserRepository.get_user_by_id(curr_uid)
        next_user = await UserRepository.get_user_by_id(next_uid)
        return curr_user, next_user, curr_idx

    @staticmethod
    async def record_room_water_delivery(room_id: int, brought_by_user_id: int, photo_file_id: str) -> Dict[str, Any]:
        now_str = datetime.now().isoformat()
        log_id = await WaterRepository.add_room_water_log(room_id, brought_by_user_id, photo_file_id, now_str)

        queue_ids = ROOM_1_WATER_QUEUE if room_id == 1 else ROOM_2_WATER_QUEUE

        # Recalculate water queue starting from bringer
        if brought_by_user_id in queue_ids:
            bringer_idx = queue_ids.index(brought_by_user_id)
        else:
            bringer_idx = 0

        next_idx = (bringer_idx + 1) % len(queue_ids)
        await WaterRepository.set_room_water_index(room_id, next_idx)

        brought_user = await UserRepository.get_user_by_id(brought_by_user_id)
        next_user = await UserRepository.get_user_by_id(queue_ids[next_idx])

        return {
            "log_id": log_id,
            "room_id": room_id,
            "brought_by": brought_user,
            "next_user": next_user,
            "next_index": next_idx
        }
