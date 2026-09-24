import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from database.repositories import (
    SettingsRepository,
    TaskRepository,
    DeepCleanRepository
)
from services.queue_service import QueueService
from keyboards.inline import build_task_checklist_keyboard
from utils.cleanup import schedule_group_message_deletion, GROUP_MESSAGE_LIFETIME_SECONDS

logger = logging.getLogger("kvartira_bot.notifier")


def format_user_tag(user: Optional[Dict[str, Any]]) -> str:
    """Format user with Telegram link mention if telegram_id exists, else bold name."""
    if not user:
        return "Noma'lum"
    name = user.get("name", "Noma'lum")
    tg_id = user.get("telegram_id")
    if tg_id:
        return f"<a href='tg://user?id={tg_id}'>{name}</a>"
    return f"<b>{name}</b>"


def format_users_tags(users: List[Dict[str, Any]]) -> str:
    if not users:
        return "Hech kim"
    return ", ".join([format_user_tag(u) for u in users])


async def get_effective_group_chat_id() -> Optional[int]:
    """Retrieve saved group ID from DB or fallback to config."""
    return await SettingsRepository.get_group_chat_id()


async def send_group_message(
    bot: Bot,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    photo: Optional[str] = None,
    chat_id: Optional[int] = None
) -> bool:
    """
    Sends a message or photo to the apartment group chat.
    Uses dynamic group_chat_id stored in database or fallback.
    """
    target_chat_id = chat_id or await get_effective_group_chat_id()
    if not target_chat_id:
        logger.warning("Guruh chat ID topilmadi. Bildirishnoma yuborilmadi.")
        return False

    try:
        if photo:
            sent_msg = await bot.send_photo(
                chat_id=target_chat_id,
                photo=photo,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            sent_msg = await bot.send_message(
                chat_id=target_chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )

        if sent_msg:
            await schedule_group_message_deletion(
                bot=bot,
                message=sent_msg,
                delay_seconds=GROUP_MESSAGE_LIFETIME_SECONDS
            )

        return True
    except Exception as e:
        logger.error(f"Guruhga xabar yuborishda xatolik ({target_chat_id}): {e}")
        return False



async def broadcast_change(
    bot: Bot,
    title: str,
    details: str,
    icon: str = "🔄",
    chat_id: Optional[int] = None
) -> bool:
    """
    Sends an announcement about a schedule/task/duty change to the group chat.
    """
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    text = (
        f"{icon} <b>O'ZGARISH: {title.upper()}</b>\n"
        f"⏰ <i>Vaqt: {time_str}</i>\n\n"
        f"{details}"
    )
    return await send_group_message(bot, text, chat_id=chat_id)


async def send_morning_brief_to_group(bot: Bot, chat_id: Optional[int] = None) -> bool:
    """
    Generates and sends the complete morning briefing to the group chat.
    Tags daily duty, laundry, water and weekly pair members.
    """
    from config import settings
    today = datetime.now(settings.timezone).date()
    today_str = today.strftime("%Y-%m-%d")

    daily_users = await QueueService.get_daily_duty(today)
    laundry_users = await QueueService.get_laundry_duty(today)
    r1_water_user, _, _ = await QueueService.get_room_water_duty_info(1)
    r2_water_user, _, _ = await QueueService.get_room_water_duty_info(2)
    active_pair_info = await QueueService.get_active_weekly_pair(today)

    daily_tags = format_users_tags(daily_users)
    laundry_tags = format_users_tags(laundry_users)
    r1_water_tag = format_user_tag(r1_water_user)
    r2_water_tag = format_user_tag(r2_water_user)

    m1_tag = format_user_tag(active_pair_info.get("member1"))
    m2_tag = format_user_tag(active_pair_info.get("member2"))
    pair_str = f"{m1_tag} & {m2_tag} ({active_pair_info.get('week_number_in_month', 1)}-hafta)"

    text = (
        f"☀️ <b>Xayrli tong, xonadoshlar! Kunlik brifing</b> ({today_str})\n\n"
        f"👨‍🍳 <b>Bugungi navbatchi:</b> {daily_tags}\n"
        f"   <i>(Dasturxon, oshxona, non va axlat tozaligi sizning zimmangizda)</i>\n"
        f"🧺 <b>Kir yuvish navbati:</b> {laundry_tags}\n"
        f"🚰 <b>Suv navbati (Baklar):</b>\n"
        f"   • 🏠 1-Xona baki: {r1_water_tag}\n"
        f"   • 🚪 2-Xona baki: {r2_water_tag}\n"
        f"👥 <b>Haftalik mas'ul juftlik (Bozorlik & Uborqa):</b> {pair_str}\n\n"
        f"📋 <b>Kunlik vazifalar nazorati (Tugmalarni bosib belgilang):</b>"
    )

    tasks = await TaskRepository.get_daily_tasks(today_str)
    keyboard = build_task_checklist_keyboard(today_str, tasks)

    return await send_group_message(bot, text, reply_markup=keyboard, chat_id=chat_id)
