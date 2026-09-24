from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from database.repositories import UserRepository, DutyRepository, WaterRepository


# Dual-Room Independent Water Queues
# Room 1 (10L Baklashka): Faqat Avazbek (1) va Firdavs (2) suv olib keladi
ROOM_1_WATER_QUEUE = [1, 2]

# Room 2: Asadbek (7), Jaloliddin (6), Mavlonbek (8) har biri 2 martadan, Ilyosbek (5) 1 marta
# Sequence: Asadbek, Jaloliddin, Mavlonbek, Asadbek, Jaloliddin, Mavlonbek, Ilyosbek (7 ta slot)
ROOM_2_WATER_QUEUE = [7, 6, 8, 7, 6, 8, 5]

# Default Daily Duty Rotations (0=Mon, 1=Tue, ..., 6=Sun)
# Omadbek excluded per request
DEFAULT_DAILY_DUTY = {
    0: [6],       # Dushanba: Jaloliddin
    1: [3],       # Seshanba: Asadbek bro
    2: [7],       # Chorshanba: Asadbek (men)
    3: [2],       # Payshanba: Firdavs
    4: [8],       # Juma: Mavlonbek
    5: [1],       # Shanba: Avazbek
    6: [5]        # Yakshanba: Ilyosbek
}

# Default Laundry Duty Rotations (0=Mon, 1=Tue, ..., 6=Sun)
DEFAULT_LAUNDRY_DUTY = {
    0: [2],       # Dushanba: Firdavs
    1: [6],       # Seshanba: Jaloliddin
    2: [3],       # Chorshanba: Asadbek bro
    3: [1],       # Payshanba: Avazbek
    4: [7],       # Juma: Asadbek
    5: [5],       # Shanba: Ilyosbek
    6: [8]        # Yakshanba: Mavlonbek
}

# Monthly 4-Week Rotating Pairs (Bozorlik & General Uborqa) - Omadbek excluded
MONTHLY_DEFAULT_PAIRS = {
    0: (1, 3, 1),  # 1-hafta (1–7 kunlar): Juftlik #1 -> Asadbek bro (3) & Avazbek (1)
    1: (2, 1, 2),  # 2-hafta (8–14 kunlar): Juftlik #2 -> Avazbek (1) & Firdavs (2)
    2: (3, 8, 7),  # 3-hafta (15–21 kunlar): Juftlik #3 -> Mavlonbek (8) & Asadbek (7)
    3: (4, 5, 6)   # 4-hafta (22–oy oxiri): Juftlik #4 -> Ilyosbek (5) & Jaloliddin (6)
}


DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
MONTH_WEEK_NAMES = ["1-hafta (1–7 kunlar)", "2-hafta (8–14 kunlar)", "3-hafta (15–21 kunlar)", "4-hafta (22–oy oxiri)"]



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
        n = len(queue_ids)
        curr_idx = await WaterRepository.get_room_water_index(room_id)

        # Advance queue: if current expected person brought it, move to next slot.
        # Otherwise, find the next upcoming slot for brought_by_user_id and advance past it.
        if queue_ids[curr_idx % n] == brought_by_user_id:
            next_idx = (curr_idx + 1) % n
        else:
            found_idx = None
            for step in range(n):
                check_idx = (curr_idx + step) % n
                if queue_ids[check_idx] == brought_by_user_id:
                    found_idx = check_idx
                    break
            if found_idx is not None:
                next_idx = (found_idx + 1) % n
            else:
                next_idx = (curr_idx + 1) % n

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

