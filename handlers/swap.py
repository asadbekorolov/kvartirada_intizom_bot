import uuid
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import SwapStates
from config import settings
from services.queue_service import QueueService
from database.repositories import UserRepository, SwapRepository, DutyRepository
from keyboards.inline import (
    build_swap_days_keyboard,
    build_swap_users_keyboard,
    build_swap_approval_keyboard,
    DAY_NAMES
)

router = Router()


@router.message(Command("almashish"))
@router.message(F.text == "🔄 Navbat almashish")
async def cmd_swap_start(message: Message, state: FSMContext, current_user: dict):
    if not current_user:
        await message.answer(
            "⚠️ Navbat almashish uchun avval Telegram hisobingizni xonadon profiliga bog'lashingiz kerak! (/start)"
        )
        return

    keyboard = build_swap_days_keyboard()
    await state.set_state(SwapStates.selecting_target_day)
    await message.answer(
        f"🔄 <b>Navbat almashish so'rovi</b>\n\n"
        f"Salom, <b>{current_user['name']}</b>! Qaysi kungi navbatchilikni almashmoqchisiz?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("swap_day:"), SwapStates.selecting_target_day)
async def callback_select_swap_day(callback: CallbackQuery, state: FSMContext, current_user: dict):
    day_idx = int(callback.data.split(":")[1])
    day_name = DAY_NAMES[day_idx]

    await state.update_data(day_idx=day_idx, day_name=day_name)
    await state.set_state(SwapStates.selecting_target_user)

    users = await UserRepository.get_all_users()
    requester_id = current_user["id"] if current_user else None
    keyboard = build_swap_users_keyboard(users, exclude_id=requester_id)

    await callback.message.edit_text(
        f"📅 Tanlangan kun: <b>{day_name}</b>\n\n"
        f"Ushbu kun uchun o'rningizga kim navbatchilik qilishini xohlaysiz?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "swap_cancel")
async def callback_cancel_swap(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Navbat almashish so'rovi bekor qilindi.")


@router.callback_query(F.data.startswith("swap_user:"), SwapStates.selecting_target_user)
async def callback_select_swap_user(callback: CallbackQuery, state: FSMContext, current_user: dict):
    target_user_id = int(callback.data.split(":")[1])
    target_user = await UserRepository.get_user_by_id(target_user_id)

    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    fsm_data = await state.get_data()
    day_idx = fsm_data["day_idx"]
    day_name = fsm_data["day_name"]

    requester_id = current_user["id"]
    requester_name = current_user["name"]

    # Calculate target date in current week
    today = datetime.now(settings.timezone).date()
    start_of_week = today - timedelta(days=today.weekday())
    target_date = start_of_week + timedelta(days=day_idx)
    target_date_str = target_date.strftime("%Y-%m-%d")

    request_id = f"swap_{uuid.uuid4().hex[:8]}"
    await SwapRepository.create_swap_request(
        request_id=request_id,
        requester_id=requester_id,
        target_id=target_user_id,
        day_of_week=day_idx,
        target_date=target_date_str
    )

    await state.clear()

    target_tag = f"<b>{target_user['name']}</b>"
    if target_user.get("telegram_id"):
        target_tag = f"<a href='tg://user?id={target_user['telegram_id']}'>{target_user['name']}</a>"

    approval_text = (
        f"🔄 <b>NAVBATCHILIK ALMASHISH SO'ROVI</b>\n\n"
        f"👤 <b>So'rovchi:</b> {requester_name}\n"
        f"🎯 <b>Mo'ljallangan sherik:</b> {target_tag}\n"
        f"📅 <b>Kun:</b> {day_name} ({target_date_str})\n\n"
        f"Hurmatli {target_tag}, <b>{requester_name}</b> {day_name} kungi navbatchilikni siz bilan almashmoqchi.\n"
        f"Rozimisiz?"
    )

    keyboard = build_swap_approval_keyboard(request_id)
    await callback.message.edit_text("✅ So'rov yuborildi. Kutilmoqda...")
    await callback.message.answer(
        text=approval_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("swap_approve:"))
async def callback_approve_swap(callback: CallbackQuery, current_user: dict):
    request_id = callback.data.split(":")[1]
    req = await SwapRepository.get_swap_request(request_id)

    if not req:
        await callback.answer("So'rov topilmadi yoki muddati o'tgan!", show_alert=True)
        return

    if req["status"] != "PENDING":
        await callback.answer(f"Ushbu so'rov allaqachon ko'rib chiqilgan ({req['status']})!", show_alert=True)
        return

    target_id = req["target_id"]
    if current_user and current_user["id"] != target_id:
        await callback.answer("Ushbu so'rov sizga yuborilmagan!", show_alert=True)
        return

    # Process Approval
    await SwapRepository.update_swap_status(request_id, "APPROVED")

    day_idx = req["day_of_week"]
    target_date = datetime.strptime(req["target_date"], "%Y-%m-%d").date()
    _, week_num, _ = target_date.isocalendar()

    # Mutate daily_overrides to assign target_id for that day
    await DutyRepository.set_daily_override(week_num, day_idx, str(target_id))

    requester = await UserRepository.get_user_by_id(req["requester_id"])
    target = await UserRepository.get_user_by_id(req["target_id"])
    day_name = DAY_NAMES[day_idx]

    success_text = (
        f"✅ <b>NAVBATCHILIK ALMASHIShI TASDIQLANDI!</b>\n\n"
        f"📅 <b>Kun:</b> {day_name} ({req['target_date']})\n"
        f"🔄 <b>Yangi navbatchi:</b> <b>{target['name']}</b> ({requester['name']} o'rniga)\n\n"
        f"Jadvalga o'zgartirish muvaffaqiyatli kiritildi!"
    )

    await callback.message.edit_text(success_text, parse_mode="HTML")


@router.callback_query(F.data.startswith("swap_reject:"))
async def callback_reject_swap(callback: CallbackQuery, current_user: dict):
    request_id = callback.data.split(":")[1]
    req = await SwapRepository.get_swap_request(request_id)

    if not req:
        await callback.answer("So'rov topilmadi!", show_alert=True)
        return

    if req["status"] != "PENDING":
        await callback.answer(f"Ushbu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    target_id = req["target_id"]
    if current_user and current_user["id"] != target_id:
        await callback.answer("Ushbu so'rov sizga yuborilmagan!", show_alert=True)
        return

    await SwapRepository.update_swap_status(request_id, "REJECTED")

    requester = await UserRepository.get_user_by_id(req["requester_id"])
    target = await UserRepository.get_user_by_id(req["target_id"])

    reject_text = (
        f"❌ <b>NAVBATCHILIK ALMASHIShI RAD ETILDI</b>\n\n"
        f"<b>{target['name']}</b> {requester['name']} ning navbat almashish so'rovini rad etdi."
    )

    await callback.message.edit_text(reject_text, parse_mode="HTML")
