from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings
from services.queue_service import QueueService
from database.repositories import TaskRepository, DutyRepository, DeepCleanRepository
from keyboards.inline import build_task_checklist_keyboard, build_deep_clean_keyboard


async def send_morning_brief(bot: Bot):
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

    await bot.send_message(
        chat_id=settings.GROUP_CHAT_ID,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def send_evening_trash_reminder(bot: Bot):
    today = datetime.now(settings.timezone).date()
    today_str = today.strftime("%Y-%m-%d")

    tasks = await TaskRepository.get_daily_tasks(today_str)
    trash_task = tasks.get("trash", {"is_completed": False})

    if not trash_task["is_completed"]:
        daily_users = await QueueService.get_daily_duty(today)
        tags = []
        for u in daily_users:
            if u.get("telegram_id"):
                tags.append(f"<a href='tg://user?id={u['telegram_id']}'>{u['name']}</a>")
            else:
                tags.append(f"<b>{u['name']}</b>")
        tag_str = ", ".join(tags)

        text = (
            f"🚨 <b>ESLATMA (21:30): Axlat to'kildimi?</b> 🚨\n\n"
            f"Hurmatli navbatchi {tag_str}, kunlik vazifalardan <b>Axlat to'kish (Oshxona & Tualet)</b> "
            f"hali bajarilmadi! Iltimos, axlatni to'kib, botda <b>[ ✅ Axlat to'kish ]</b> tugmasini bosing!"
        )

        keyboard = build_task_checklist_keyboard(today_str, tasks)
        await bot.send_message(
            chat_id=settings.GROUP_CHAT_ID,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


async def send_sunday_deep_clean_brief(bot: Bot):
    today = datetime.now(settings.timezone).date()
    if today.weekday() != 6:
        return

    today_str = today.strftime("%Y-%m-%d")
    pair_info = await QueueService.get_active_weekly_pair(today)
    m1_name = pair_info['member1']['name'] if pair_info['member1'] else "?"
    m2_name = pair_info['member2']['name'] if pair_info['member2'] else "?"
    pair_names = f"<b>{m1_name} & {m2_name}</b> ({pair_info['week_number_in_month']}-hafta)"

    text = (
        f"🧹 <b>YAKSHANBALIK GENERAL UBORQA (09:00)</b> 🧹\n\n"
        f"Bugungi general tozalik mas'ullari: {pair_names}\n\n"
        f"Iltimos, uborqa yakunlangach quyidagi 11 ta nazorat punktini belgilab chiqing:"
    )

    tasks = await DeepCleanRepository.get_deep_clean_tasks(today_str)
    keyboard = build_deep_clean_keyboard(today_str, tasks)

    await bot.send_message(
        chat_id=settings.GROUP_CHAT_ID,
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


async def reset_weekly_overrides_job():
    today = datetime.now(settings.timezone).date()
    _, week_num, _ = today.isocalendar()
    await DutyRepository.clear_weekly_overrides(week_num)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    # 1. Daily Morning Brief (07:30 Tashkent Time)
    scheduler.add_job(
        send_morning_brief,
        trigger=CronTrigger(hour=7, minute=30, timezone=settings.timezone),
        args=[bot],
        id="morning_brief"
    )

    # 2. Evening Trash Reminder (21:30 Tashkent Time)
    scheduler.add_job(
        send_evening_trash_reminder,
        trigger=CronTrigger(hour=21, minute=30, timezone=settings.timezone),
        args=[bot],
        id="evening_trash_reminder"
    )

    # 3. Sunday Deep Clean Inspection Brief (Sunday 09:00 Tashkent Time)
    scheduler.add_job(
        send_sunday_deep_clean_brief,
        trigger=CronTrigger(day_of_week="sun", hour=9, minute=0, timezone=settings.timezone),
        args=[bot],
        id="sunday_deep_clean_brief"
    )

    # 4. Sunday Auto-Reset Weekly Overrides (Sunday 23:59 Tashkent Time)
    scheduler.add_job(
        reset_weekly_overrides_job,
        trigger=CronTrigger(day_of_week="sun", hour=23, minute=59, timezone=settings.timezone),
        id="reset_weekly_overrides"
    )

    return scheduler
