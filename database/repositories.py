from typing import List, Optional, Dict, Any
from datetime import datetime
from database.connection import get_db


class UserRepository:
    @staticmethod
    async def get_all_users() -> List[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users ORDER BY id ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    async def get_users_by_room(room_number: int) -> List[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE room_number = ? ORDER BY id ASC", (room_number,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def bind_telegram_id(user_id: int, telegram_id: int) -> bool:
        async with get_db() as db:
            await db.execute("UPDATE users SET telegram_id = ? WHERE id = ?", (telegram_id, user_id))
            await db.commit()
            return True

    @staticmethod
    async def set_admin(user_id: int, is_admin: bool) -> bool:
        async with get_db() as db:
            await db.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))
            await db.commit()
            return True


class DutyRepository:
    @staticmethod
    async def get_daily_override(week_number: int, day_of_week: int) -> Optional[str]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT assigned_user_ids FROM daily_overrides WHERE week_number = ? AND day_of_week = ?",
                (week_number, day_of_week)
            )
            row = await cursor.fetchone()
            return row["assigned_user_ids"] if row else None

    @staticmethod
    async def set_daily_override(week_number: int, day_of_week: int, assigned_user_ids: str):
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO daily_overrides (week_number, day_of_week, assigned_user_ids)
                VALUES (?, ?, ?)
                ON CONFLICT(week_number, day_of_week) DO UPDATE SET assigned_user_ids = excluded.assigned_user_ids
                """,
                (week_number, day_of_week, assigned_user_ids)
            )
            await db.commit()

    @staticmethod
    async def clear_weekly_overrides(week_number: int):
        async with get_db() as db:
            await db.execute("DELETE FROM daily_overrides WHERE week_number = ?", (week_number,))
            await db.commit()

    @staticmethod
    async def get_weekly_pair_assignment(month_year: str, week_index: int) -> Optional[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT * FROM weekly_pair_assignments
                WHERE month_year = ? AND week_index = ?
                """,
                (month_year, week_index)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def set_weekly_pair_assignment(
        month_year: str, week_index: int, pair_id: int, member1_id: int, member2_id: int
    ):
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO weekly_pair_assignments (month_year, week_index, pair_id, member1_id, member2_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(month_year, week_index) DO UPDATE SET
                    pair_id = excluded.pair_id,
                    member1_id = excluded.member1_id,
                    member2_id = excluded.member2_id
                """,
                (month_year, week_index, pair_id, member1_id, member2_id)
            )
            await db.commit()

    @staticmethod
    async def clear_weekly_pair_assignment(month_year: str, week_index: int):
        async with get_db() as db:
            await db.execute(
                "DELETE FROM weekly_pair_assignments WHERE month_year = ? AND week_index = ?",
                (month_year, week_index)
            )
            await db.commit()


class TaskRepository:
    CORE_TASKS = ["cooking", "bread", "table_dishes", "trash"]

    @staticmethod
    async def get_daily_tasks(log_date: str) -> Dict[str, Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM daily_task_logs WHERE log_date = ?", (log_date,)
            )
            rows = await cursor.fetchall()
            result = {task_key: {"is_completed": False, "completed_by": None, "completed_at": None}
                      for task_key in TaskRepository.CORE_TASKS}
            for row in rows:
                result[row["task_key"]] = {
                    "is_completed": bool(row["is_completed"]),
                    "completed_by": row["completed_by"],
                    "completed_at": row["completed_at"]
                }
            return result

    @staticmethod
    async def toggle_task(log_date: str, task_key: str, user_id: int) -> Dict[str, Any]:
        tasks = await TaskRepository.get_daily_tasks(log_date)
        current = tasks.get(task_key, {"is_completed": False})
        new_state = not current["is_completed"]
        now_str = datetime.now().isoformat() if new_state else None

        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO daily_task_logs (log_date, task_key, is_completed, completed_by, completed_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(log_date, task_key) DO UPDATE SET
                    is_completed = excluded.is_completed,
                    completed_by = excluded.completed_by,
                    completed_at = excluded.completed_at
                """,
                (log_date, task_key, 1 if new_state else 0, user_id if new_state else None, now_str)
            )
            await db.commit()

        updated_tasks = await TaskRepository.get_daily_tasks(log_date)
        all_completed = all(t["is_completed"] for t in updated_tasks.values())
        return {
            "task_key": task_key,
            "new_state": new_state,
            "all_completed": all_completed,
            "tasks": updated_tasks
        }

    @staticmethod
    async def reset_daily_tasks(log_date: str):
        async with get_db() as db:
            await db.execute("DELETE FROM daily_task_logs WHERE log_date = ?", (log_date,))
            await db.commit()


class WaterRepository:
    @staticmethod
    async def get_room_water_index(room_id: int) -> int:
        async with get_db() as db:
            cursor = await db.execute("SELECT current_user_index FROM room_water_state WHERE room_id = ?", (room_id,))
            row = await cursor.fetchone()
            return row["current_user_index"] if row else 0

    @staticmethod
    async def set_room_water_index(room_id: int, new_index: int):
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO room_water_state (room_id, current_user_index)
                VALUES (?, ?)
                ON CONFLICT(room_id) DO UPDATE SET current_user_index = excluded.current_user_index
                """,
                (room_id, new_index % 4)
            )
            await db.commit()

    @staticmethod
    async def add_room_water_log(room_id: int, brought_by_user_id: int, photo_file_id: str, created_at: str) -> int:
        async with get_db() as db:
            cursor = await db.execute(
                """
                INSERT INTO room_water_logs (room_id, brought_by_user_id, photo_file_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (room_id, brought_by_user_id, photo_file_id, created_at)
            )
            await db.commit()
            return cursor.lastrowid

    @staticmethod
    async def get_room_water_logs(room_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT wl.*, u.name as brought_by_name
                FROM room_water_logs wl
                JOIN users u ON wl.brought_by_user_id = u.id
                WHERE wl.room_id = ?
                ORDER BY wl.id DESC LIMIT ?
                """,
                (room_id, limit)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    async def get_all_recent_water_logs(limit: int = 10) -> List[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute(
                """
                SELECT wl.*, u.name as brought_by_name
                FROM room_water_logs wl
                JOIN users u ON wl.brought_by_user_id = u.id
                ORDER BY wl.id DESC LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


class SwapRepository:
    @staticmethod
    async def create_swap_request(
        request_id: str, requester_id: int, target_id: int, swap_type: str, target_info: str
    ):
        async with get_db() as db:
            now_str = datetime.now().isoformat()
            await db.execute(
                """
                INSERT INTO swap_requests (id, requester_id, target_id, swap_type, target_info, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
                """,
                (request_id, requester_id, target_id, swap_type, target_info, now_str)
            )
            await db.commit()

    @staticmethod
    async def get_swap_request(request_id: str) -> Optional[Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute("SELECT * FROM swap_requests WHERE id = ?", (request_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def update_swap_status(request_id: str, status: str):
        async with get_db() as db:
            await db.execute("UPDATE swap_requests SET status = ? WHERE id = ?", (status, request_id))
            await db.commit()


class DeepCleanRepository:
    ITEMS = [
        "oshxona_pol", "oshxona_plita", "xontaxta_va_stollar", "tualet_santexnika",
        "tualet_pol", "banya_tozaligi", "koridor_pol", "kirxona_tartibi",
        "axlat_qutilari", "muzlatgich_tashqi", "derazalar_va_eshiklar"
    ]

    @staticmethod
    async def get_deep_clean_tasks(log_date: str) -> Dict[str, Dict[str, Any]]:
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM deep_clean_logs WHERE log_date = ?", (log_date,)
            )
            rows = await cursor.fetchall()
            result = {item_key: {"is_completed": False, "completed_by": None, "completed_at": None}
                      for item_key in DeepCleanRepository.ITEMS}
            for row in rows:
                result[row["item_key"]] = {
                    "is_completed": bool(row["is_completed"]),
                    "completed_by": row["completed_by"],
                    "completed_at": row["completed_at"]
                }
            return result

    @staticmethod
    async def toggle_deep_clean_task(log_date: str, item_key: str, user_id: int) -> Dict[str, Any]:
        tasks = await DeepCleanRepository.get_deep_clean_tasks(log_date)
        current = tasks.get(item_key, {"is_completed": False})
        new_state = not current["is_completed"]
        now_str = datetime.now().isoformat() if new_state else None

        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO deep_clean_logs (log_date, item_key, is_completed, completed_by, completed_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(log_date, item_key) DO UPDATE SET
                    is_completed = excluded.is_completed,
                    completed_by = excluded.completed_by,
                    completed_at = excluded.completed_at
                """,
                (log_date, item_key, 1 if new_state else 0, user_id if new_state else None, now_str)
            )
            await db.commit()

        updated = await DeepCleanRepository.get_deep_clean_tasks(log_date)
        all_completed = all(t["is_completed"] for t in updated.values())
        return {
            "item_key": item_key,
            "new_state": new_state,
            "all_completed": all_completed,
            "tasks": updated
        }
