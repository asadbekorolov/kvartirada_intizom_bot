from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from config import settings
from services.queue_service import QueueService
from database.repositories import TaskRepository, DeepCleanRepository, UserRepository
from keyboards.inline import build_task_checklist_keyboard, build_deep_clean_keyboard, TASK_LABELS, DEEP_CLEAN_LABELS

router = Router()


@router.message(Command("bugun"))
@router.message(F.text == "📋 Bugungi navbatchilik")
async def cmd_today_duty(message: Message):
    today = datetime.now(settings.timezone).date()
    today_str = today.strftime("%Y-%m-%d")

    daily_users = await QueueService.get_daily_duty(today)
    laundry_users = await QueueService.get_laundry_duty(today)
    curr_water_user, _, _ = await QueueService.get_water_duty_info()

    daily_names = ", ".join([f"<b>{u['name']}</b>" for u in daily_users])
    laundry_names = ", ".join([f"<b>{u['name']}</b>" for u in laundry_users])
    water_name = f"<b>{curr_water_user['name']}</b>" if curr_water_user else "Noma'lum"

    text = (
        f"☀️ <b>Kvartira Bot — Bugungi kunlik brifing</b> ({today_str})\n\n"
        f"👨‍🍳 <b>Kunning navbatchisi:</b> {daily_names}\n"
        f"🧺 <b>Kir yuvish navbati:</b> {laundry_names}\n"
        f"🚰 <b>Suv olib kelish navbati:</b> {water_name}\n\n"
        f"📋 <b>Vazifalar ro'yxati (Tugmalarni bosib belgilang):</b>"
    )

    tasks = await TaskRepository.get_daily_tasks(today_str)
    keyboard = build_task_checklist_keyboard(today_str, tasks)

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


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
    state_str = "bajarildi deb belgilandi ✅" if new_state else "bekor qilindi ❌"

    await callback.answer(f"'{task_name}' {state_str}")

    # Update inline keyboard dynamically
    new_keyboard = build_task_checklist_keyboard(log_date, result["tasks"])
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    # Celebration notification when all 4 tasks are completed
    if all_completed and new_state:
        completed_by_name = current_user["name"] if current_user else callback.from_user.full_name
        celebration_text = (
            f"🎉 <b>BARCHA VAZIFALAR BAJARILDI!</b> 🎉\n\n"
            f"Hurmatli xonadoshlar, bugungi ({log_date}) barcha 4 ta kunlik vazifalar "
            f"muvaffaqiyatli yakunlandi!\n"
            f"Oxirgi vazifani belgiladi: <b>{completed_by_name}</b>.\n"
            f"Katta rahmat! Oila a'zolarimizga halovat va tozalik tilaymiz! ✨👏"
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
            f"Barcha 11 ta nazorat punktlari to'liq bajariib chiqildi. Baraka topsin navbatchilar! 🧹👏"
        )
        await callback.message.answer(celebration_text, parse_mode="HTML")
