from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from config import settings
from services.queue_service import QueueService
from database.repositories import TaskRepository, DeepCleanRepository
from keyboards.inline import build_task_checklist_keyboard, build_deep_clean_keyboard, TASK_LABELS, DEEP_CLEAN_LABELS
from utils.cleanup import safe_delete, delete_after

router = Router()


@router.message(Command("bugun"))
@router.message(F.text == "📋 Bugungi navbatchilik")
async def cmd_today_duty(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    today = datetime.now(settings.timezone).date()
    today_str = today.strftime("%Y-%m-%d")

    daily_users = await QueueService.get_daily_duty(today)
    laundry_users = await QueueService.get_laundry_duty(today)
    r1_water_user, _, _ = await QueueService.get_room_water_duty_info(1)
    r2_water_user, _, _ = await QueueService.get_room_water_duty_info(2)
    active_pair_info = await QueueService.get_active_weekly_pair(today)

    daily_names = ", ".join([f"<b>{u['name']}</b>" for u in daily_users])
    laundry_names = ", ".join([f"<b>{u['name']}</b>" for u in laundry_users])
    r1_water_name = f"<b>{r1_water_user['name']}</b>" if r1_water_user else "Noma'lum"
    r2_water_name = f"<b>{r2_water_user['name']}</b>" if r2_water_user else "Noma'lum"

    m1_name = active_pair_info['member1']['name'] if active_pair_info['member1'] else "?"
    m2_name = active_pair_info['member2']['name'] if active_pair_info['member2'] else "?"
    pair_str = f"<b>{m1_name} & {m2_name}</b> ({active_pair_info['week_number_in_month']}-hafta)"

    text = (
        f"☀️ <b>Kvartira Bot — Bugungi kunlik brifing</b> ({today_str})\n\n"
        f"👨‍🍳 <b>Kunning navbatchisi:</b> {daily_names}\n"
        f"🧺 <b>Kir yuvish navbati:</b> {laundry_names}\n"
        f"🚰 <b>Suv navbati:</b>\n"
        f"   • 🏠 1-Xona baki: {r1_water_name}\n"
        f"   • 🚪 2-Xona baki: {r2_water_name}\n"
        f"👥 <b>Haftalik mas'ul juftlik (Bozorlik & Uborqa):</b> {pair_str}\n\n"
        f"📋 <b>Vazifalar ro'yxati (Tugmalarni bosib belgilang):</b>"
    )

    tasks = await TaskRepository.get_daily_tasks(today_str)
    keyboard = build_task_checklist_keyboard(today_str, tasks)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(Command("hafta"))
@router.message(F.text == "🗓 Haftalik navbatchilik (Bozorlik)")
async def cmd_week_pair(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    today = datetime.now(settings.timezone).date()
    curr_week_idx = QueueService.get_month_week_index(today)
    active_pair_info = await QueueService.get_active_weekly_pair(today)

    m1_active = active_pair_info['member1']['name'] if active_pair_info['member1'] else "?"
    m2_active = active_pair_info['member2']['name'] if active_pair_info['member2'] else "?"

    text = (
        f"🗓 <b>HAFTALIK NAVBATCHILIK VA BOZORLIK REJASI</b>\n\n"
        f"🌟 <b>HOZIRGI FAOL HAFTA ({curr_week_idx + 1}-hafta):</b>\n"
        f"👥 <b>Mas'ul juftlik:</b> <b>{m1_active} & {m2_active}</b>\n"
        f"🛒 <b>Vazifalar:</b> Umumiy bozorlik qilish + Yakshanbalik general uborqa\n"
        f"📌 <b>Holat:</b> {'🔄 (Almashuv kiritilgan)' if active_pair_info['is_overridden'] else '✅ (Standart reja)'}\n\n"
        f"📋 <b>OYLIK TO'LIQ ROTATSIYA JADVALI:</b>\n"
    )

    from services.queue_service import MONTH_WEEK_NAMES
    for w_idx in range(4):
        sample_day = min(w_idx * 7 + 1, 28)
        sample_date = date(today.year, today.month, sample_day)
        p_info = await QueueService.get_active_weekly_pair(sample_date)
        m1 = p_info['member1']['name'] if p_info['member1'] else "?"
        m2 = p_info['member2']['name'] if p_info['member2'] else "?"
        
        prefix = "➡️" if w_idx == curr_week_idx else "•"
        tag = " <i>(Hozirgi faol)</i>" if w_idx == curr_week_idx else ""
        override_tag = " 🔄" if p_info['is_overridden'] else ""
        
        text += f"{prefix} <b>{MONTH_WEEK_NAMES[w_idx]}:</b> {m1} & {m2}{override_tag}{tag}\n"

    msg = await message.answer(text, parse_mode="HTML")
    if is_group:
        await delete_after(msg, 60)



@router.callback_query(F.data.startswith("task_toggle:"))
async def callback_toggle_task(callback: CallbackQuery, current_user: dict):
    parts = callback.data.split(":")
    log_date = parts[1]
    task_key = parts[2]

    user_id = current_user["id"] if current_user else None

    result = await TaskRepository.toggle_task(log_date, task_key, user_id)
    new_state = result["new_state"]
    all_completed = result["all_completed"]

    task_name = TASK_LABELS.get(task_key, task_key)
    state_str = "bajarildi ✅" if new_state else "bekor qilindi ❌"

    await callback.answer(f"'{task_name}' {state_str}")

    # Single-message pattern: in-place keyboard update
    new_keyboard = build_task_checklist_keyboard(log_date, result["tasks"])
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    # Celebration notification when all 4 tasks are completed
    if all_completed and new_state:
        completed_by_name = current_user["name"] if current_user else callback.from_user.full_name
        celebration_text = (
            f"🎉 <b>BARCHA KUNLIK VAZIFALAR BAJARILDI!</b> 🎉\n\n"
            f"Bugungi ({log_date}) 4 ta kunlik vazifaning barchasi yakunlandi!\n"
            f"Oxirgi vazifani belgiladi: <b>{completed_by_name}</b>.\n"
            f"Katta rahmat! Xonadonga fayz va tozalik tilaymiz! ✨👏"
        )
        await callback.message.answer(celebration_text, parse_mode="HTML")


@router.callback_query(F.data.startswith("dc_toggle:"))
async def callback_toggle_deep_clean(callback: CallbackQuery, current_user: dict):
    parts = callback.data.split(":")
    log_date = parts[1]
    item_key = parts[2]

    user_id = current_user["id"] if current_user else None

    result = await DeepCleanRepository.toggle_deep_clean_task(log_date, item_key, user_id)
    new_state = result["new_state"]
    all_completed = result["all_completed"]

    item_name = DEEP_CLEAN_LABELS.get(item_key, item_key)
    state_str = "bajarildi ✅" if new_state else "bekor qilindi ❌"

    await callback.answer(f"'{item_name}' {state_str}")

    new_keyboard = build_deep_clean_keyboard(log_date, result["tasks"])
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    if all_completed and new_state:
        celebration_text = (
            f"✨ <b>YAKSHANBALIK GENERAL UBORQA MUVAFFAQIYATLI YAKUNLANDI!</b> ✨\n\n"
            f"Barcha 11 ta nazorat punktlari to'liq bajarib chiqildi. Baraka topsin navbatchilar! 🧹👏"
        )
        await callback.message.answer(celebration_text, parse_mode="HTML")
