from typing import Dict, Any, List
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


TASK_LABELS = {
    "cooking": "Taom tayyorlash",
    "bread": "Non olib kelish",
    "table_dishes": "Umumiy idishlar / xontaxta tozaligi",
    "trash": "Axlat to'kish (Oshxona & Tualet)"
}

DEEP_CLEAN_LABELS = {
    "oshxona_pol": "Oshxona polini yuvish",
    "oshxona_plita": "Gaz plitasi va pechni ardish",
    "xontaxta_va_stollar": "Xontaxta va stollarni tozalash",
    "tualet_santexnika": "Tualet va unitazni dezinfeksiya qilish",
    "tualet_pol": "Tualet polini yuvish",
    "banya_tozaligi": "Vanna/Dushxonani yuvish",
    "koridor_pol": "Koridor va kirish kismini tozalash",
    "kirxona_tartibi": "Kir yuvish xonasini tartiblash",
    "axlat_qutilari": "Axlat qutilarini yuvish va tartibga keltirish",
    "muzlatgich_tashqi": "Muzlatgich tashqi yuzasini artish",
    "derazalar_va_eshiklar": "Derazalar va eshik tutqichlarini artish"
}

DAY_NAMES = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


def build_task_checklist_keyboard(log_date: str, tasks: Dict[str, Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task_key, label in TASK_LABELS.items():
        info = tasks.get(task_key, {"is_completed": False})
        status_icon = "✅" if info["is_completed"] else "❌"
        btn_text = f"[ {status_icon} ] {label}"
        builder.button(
            text=btn_text,
            callback_data=f"task_toggle:{log_date}:{task_key}"
        )
    builder.adjust(1)
    return builder.as_markup()


def build_water_bringer_keyboard(users: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users:
        builder.button(
            text=f"👤 {u['name']} (Xona {u['room_number']})",
            callback_data=f"water_bringer:{u['id']}"
        )
    builder.button(text="❌ Bekor qilish", callback_data="water_cancel")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()


def build_swap_days_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, day_name in enumerate(DAY_NAMES):
        builder.button(
            text=f"📅 {day_name}",
            callback_data=f"swap_day:{idx}"
        )
    builder.button(text="❌ Bekor qilish", callback_data="swap_cancel")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()


def build_swap_users_keyboard(users: List[Dict[str, Any]], exclude_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users:
        if exclude_id and u["id"] == exclude_id:
            continue
        builder.button(
            text=f"👤 {u['name']}",
            callback_data=f"swap_user:{u['id']}"
        )
    builder.button(text="❌ Bekor qilish", callback_data="swap_cancel")
    builder.adjust(2)
    return builder.as_markup()


def build_swap_approval_keyboard(request_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Roziman",
        callback_data=f"swap_approve:{request_id}"
    )
    builder.button(
        text="❌ Rad etish",
        callback_data=f"swap_reject:{request_id}"
    )
    builder.adjust(2)
    return builder.as_markup()


def build_deep_clean_keyboard(log_date: str, tasks: Dict[str, Dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item_key, label in DEEP_CLEAN_LABELS.items():
        info = tasks.get(item_key, {"is_completed": False})
        status_icon = "✅" if info["is_completed"] else "❌"
        builder.button(
            text=f"[ {status_icon} ] {label}",
            callback_data=f"dc_toggle:{log_date}:{item_key}"
        )
    builder.adjust(1)
    return builder.as_markup()
