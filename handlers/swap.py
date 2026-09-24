import json
import uuid
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import SwapStates
from config import settings
from services.queue_service import QueueService, DAY_NAMES, MONTH_WEEK_NAMES, MONTHLY_DEFAULT_PAIRS
from database.repositories import UserRepository, SwapRepository, DutyRepository
from keyboards.inline import (
    build_swap_type_keyboard,
    build_swap_days_keyboard,
    build_swap_weeks_keyboard,
    build_swap_users_keyboard,
    build_swap_approval_keyboard
)
from utils.cleanup import safe_delete, delete_after
from services.notifier import send_group_message, broadcast_change

router = Router()


async def start_swap_flow_pm(message: Message, current_user: dict, state: FSMContext = None):
    if not current_user:
        await message.answer("⚠️ Navbat almashish uchun avval profilingizni tanlashingiz kerak: /start")
        return

    if state:
        await state.set_state(SwapStates.selecting_swap_type)
    await message.answer(
        f"🔄 <b>Navbatchilik almashish tizimi</b>\n\n"
        f"Salom, <b>{current_user['name']}</b>! Qaysi turdagi almashuvni amalga oshirmoqchisiz?",
        reply_markup=build_swap_type_keyboard(),
        parse_mode="HTML"
    )


@router.message(Command("almashish"))
@router.message(F.text == "🔄 Navbat almashish")
async def cmd_swap_start(message: Message, state: FSMContext, current_user: dict, bot: Bot):
    if message.chat.type in ("group", "supergroup"):
        await safe_delete(message)
        me = await bot.get_me()
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Navbat almashish (PM)", url=f"https://t.me/{me.username}?start=swap")
        ]])
        msg = await message.answer(
            "🔄 <b>Navbat almashish</b>\n\n"
            "Guruhda xabarlar ko'paymasligi uchun iltimos, botning shaxsiy chatida boshlang:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await delete_after(msg, 30)
        return

    await start_swap_flow_pm(message, current_user, state)


@router.callback_query(F.data == "swap_cancel")
async def callback_cancel_swap(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Navbat almashish bekor qilindi.")


# --- 1. Swap Type Selector ---
@router.callback_query(F.data.startswith("swap_type:"))
async def callback_select_swap_type(callback: CallbackQuery, state: FSMContext, current_user: dict):
    swap_type = callback.data.split(":")[1]
    await state.update_data(swap_type=swap_type)

    if swap_type == "daily":
        await state.set_state(SwapStates.selecting_daily_day)
        await callback.message.edit_text(
            "📅 <b>Kunlik navbatchilikni almashish</b>\n\n"
            "Qaysi kungi navbatchilikni boshqa xonadosh bilan almashmoqchisiz?",
            reply_markup=build_swap_days_keyboard(),
            parse_mode="HTML"
        )
    elif swap_type == "weekly_pair":
        today = datetime.now(settings.timezone).date()
        curr_week_idx = QueueService.get_month_week_index(today)
        await state.update_data(my_week_idx=curr_week_idx)
        await state.set_state(SwapStates.selecting_pair_target_week)
        await callback.message.edit_text(
            f"👥 <b>Butun haftalik juftlik mas'uliyatini almashish</b>\n\n"
            f"Sizning joriy haftangiz: <b>{MONTH_WEEK_NAMES[curr_week_idx]}</b>\n"
            f"Qaysi hafta juftligi bilan to'liq almashmoqchisiz?",
            reply_markup=build_swap_weeks_keyboard(curr_week_idx),
            parse_mode="HTML"
        )
    elif swap_type == "pair_proxy":
        today = datetime.now(settings.timezone).date()
        active_pair = await QueueService.get_active_weekly_pair(today)
        all_users = await UserRepository.get_all_users()
        requester_id = current_user["id"] if current_user else None

        await state.set_state(SwapStates.selecting_proxy_target_user)
        await callback.message.edit_text(
            f"👤 <b>Juftlik ichida o'rinbosar topish</b>\n\n"
            f"Joriy {active_pair['week_number_in_month']}-haftalik juftlikdagi o'rningizga kimni vaqtincha biriktirmoqchisiz?",
            reply_markup=build_swap_users_keyboard(all_users, exclude_id=requester_id, callback_prefix="proxy_user"),
            parse_mode="HTML"
        )


# --- 2. Daily Swap Flow ---
@router.callback_query(F.data.startswith("swap_day:"), SwapStates.selecting_daily_day)
async def callback_select_daily_day(callback: CallbackQuery, state: FSMContext, current_user: dict):
    day_idx = int(callback.data.split(":")[1])
    day_name = DAY_NAMES[day_idx]
    await state.update_data(day_idx=day_idx, day_name=day_name)
    await state.set_state(SwapStates.selecting_daily_user)

    users = await UserRepository.get_all_users()
    requester_id = current_user["id"] if current_user else None
    await callback.message.edit_text(
        f"📅 Tanlangan kun: <b>{day_name}</b>\n\n"
        f"Ushbu kunda o'rningizga kim navbatchilik qilishini xohlaysiz?",
        reply_markup=build_swap_users_keyboard(users, exclude_id=requester_id, callback_prefix="daily_user"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("daily_user:"), SwapStates.selecting_daily_user)
async def callback_select_daily_user(callback: CallbackQuery, state: FSMContext, current_user: dict, bot: Bot):
    target_user_id = int(callback.data.split(":")[1])
    target_user = await UserRepository.get_user_by_id(target_user_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    fsm_data = await state.get_data()
    day_idx = fsm_data["day_idx"]
    day_name = fsm_data["day_name"]

    today = datetime.now(settings.timezone).date()
    start_of_week = today - timedelta(days=today.weekday())
    target_date = start_of_week + timedelta(days=day_idx)
    target_date_str = target_date.strftime("%Y-%m-%d")

    request_id = f"swap_{uuid.uuid4().hex[:8]}"
    payload = {
        "swap_type": "DAILY",
        "day_idx": day_idx,
        "day_name": day_name,
        "target_date_str": target_date_str
    }

    await SwapRepository.create_swap_request(
        request_id=request_id,
        requester_id=current_user["id"],
        target_id=target_user_id,
        swap_type="DAILY",
        target_info=json.dumps(payload)
    )
    await state.clear()

    target_tag = f"<b>{target_user['name']}</b>"
    if target_user.get("telegram_id"):
        target_tag = f"<a href='tg://user?id={target_user['telegram_id']}'>{target_user['name']}</a>"

    await callback.message.edit_text("✅ So'rov yaratildi. Guruhga tasdiqlash kartasi yuborildi.")

    card_text = (
        f"🔄 <b>KUNLIK NAVBATCHILIK ALMASHISH SO'ROVI</b>\n\n"
        f"👤 <b>So'rovchi:</b> {current_user['name']}\n"
        f"🎯 <b>Mo'ljallangan xonadosh:</b> {target_tag}\n"
        f"📅 <b>Kun:</b> {day_name} ({target_date_str})\n\n"
        f"Hurmatli {target_tag}, <b>{current_user['name']}</b> {day_name} kungi navbatchilikni siz bilan almashmoqchi.\n"
        f"Rozimisiz?"
    )

    await send_group_message(
        bot=bot,
        text=card_text,
        reply_markup=build_swap_approval_keyboard(request_id)
    )



# --- 3. Whole Weekly Pair Swap Flow ---
@router.callback_query(F.data.startswith("swap_week:"), SwapStates.selecting_pair_target_week)
async def callback_select_pair_target_week(callback: CallbackQuery, state: FSMContext, current_user: dict, bot: Bot):
    target_week_idx = int(callback.data.split(":")[1])
    fsm_data = await state.get_data()
    my_week_idx = fsm_data["my_week_idx"]

    today = datetime.now(settings.timezone).date()
    month_year = today.strftime("%Y-%m")

    # Current Week Pair and Target Week Pair
    my_pair_id, my_m1_id, my_m2_id = MONTHLY_DEFAULT_PAIRS[my_week_idx]
    target_pair_id, target_m1_id, target_m2_id = MONTHLY_DEFAULT_PAIRS[target_week_idx]

    target_m1 = await UserRepository.get_user_by_id(target_m1_id)
    target_m2 = await UserRepository.get_user_by_id(target_m2_id)

    request_id = f"swap_{uuid.uuid4().hex[:8]}"
    payload = {
        "swap_type": "WEEKLY_PAIR",
        "month_year": month_year,
        "my_week_idx": my_week_idx,
        "my_pair_id": my_pair_id,
        "my_m1_id": my_m1_id,
        "my_m2_id": my_m2_id,
        "target_week_idx": target_week_idx,
        "target_pair_id": target_pair_id,
        "target_m1_id": target_m1_id,
        "target_m2_id": target_m2_id
    }

    await SwapRepository.create_swap_request(
        request_id=request_id,
        requester_id=current_user["id"],
        target_id=target_m1_id, # Target Pair Leader
        swap_type="WEEKLY_PAIR",
        target_info=json.dumps(payload)
    )
    await state.clear()

    await callback.message.edit_text("✅ Haftalik juftlik almashish so'rovi yaratildi va guruhga yuborildi.")

    card_text = (
        f"👥 <b>HAFTALIK JUFTLIK ALMASHISH SO'ROVI</b>\n\n"
        f"👤 <b>Tashabbuskor:</b> {current_user['name']} (Juftlik #{my_pair_id}, {MONTH_WEEK_NAMES[my_week_idx]})\n"
        f"🎯 <b>Taklif etilgan juftlik:</b> <b>{target_m1['name']} & {target_m2['name']}</b> (Juftlik #{target_pair_id}, {MONTH_WEEK_NAMES[target_week_idx]})\n\n"
        f"Ushbu almashuv tasdiqlansa, ikkala hafta uchun bozorlik va general uborqa vazifalari to'liq almashadi.\n"
        f"Rozimisiz?"
    )

    await send_group_message(
        bot=bot,
        text=card_text,
        reply_markup=build_swap_approval_keyboard(request_id)
    )



# --- 4. Pair Member Proxy Swap Flow ---
@router.callback_query(F.data.startswith("proxy_user:"), SwapStates.selecting_proxy_target_user)
async def callback_select_proxy_user(callback: CallbackQuery, state: FSMContext, current_user: dict, bot: Bot):
    proxy_user_id = int(callback.data.split(":")[1])
    proxy_user = await UserRepository.get_user_by_id(proxy_user_id)
    if not proxy_user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    today = datetime.now(settings.timezone).date()
    month_year = today.strftime("%Y-%m")
    week_idx = QueueService.get_month_week_index(today)
    active_pair = await QueueService.get_active_weekly_pair(today)

    request_id = f"swap_{uuid.uuid4().hex[:8]}"
    payload = {
        "swap_type": "PAIR_MEMBER_PROXY",
        "month_year": month_year,
        "week_idx": week_idx,
        "pair_id": active_pair["pair_id"],
        "requester_id": current_user["id"],
        "proxy_user_id": proxy_user_id,
        "other_member_id": active_pair["member2"]["id"] if active_pair["member1"]["id"] == current_user["id"] else active_pair["member1"]["id"]
    }

    await SwapRepository.create_swap_request(
        request_id=request_id,
        requester_id=current_user["id"],
        target_id=proxy_user_id,
        swap_type="PAIR_MEMBER_PROXY",
        target_info=json.dumps(payload)
    )
    await state.clear()

    await callback.message.edit_text("✅ Juftlik ichida o'rinbosar so'rovi yaratildi va guruhga yuborildi.")

    proxy_tag = f"<b>{proxy_user['name']}</b>"
    if proxy_user.get("telegram_id"):
        proxy_tag = f"<a href='tg://user?id={proxy_user['telegram_id']}'>{proxy_user['name']}</a>"

    card_text = (
        f"👤 <b>JUFTLIK ICHIDA O'RINBOSARLIK SO'ROVI</b>\n\n"
        f"👤 <b>Asl mas'ul:</b> {current_user['name']}\n"
        f"🎯 <b>Taklif etilgan o'rinbosar:</b> {proxy_tag}\n"
        f"🗓 <b>Hafta:</b> {MONTH_WEEK_NAMES[week_idx]}\n\n"
        f"Hurmatli {proxy_tag}, <b>{current_user['name']}</b> ushbu haftalik juftlik (bozorlik va uborqa) vazifasida o'z o'rnini sizga topshirmoqchi.\n"
        f"Rozimisiz?"
    )

    await send_group_message(
        bot=bot,
        text=card_text,
        reply_markup=build_swap_approval_keyboard(request_id)
    )



# --- 5. Swap Approvals & Rejections ---
@router.callback_query(F.data.startswith("swap_approve:"))
async def callback_approve_swap(callback: CallbackQuery, current_user: dict):
    request_id = callback.data.split(":")[1]
    req = await SwapRepository.get_swap_request(request_id)

    if not req:
        await callback.answer("So'rov topilmadi yoki eskirgan!", show_alert=True)
        return

    if req["status"] != "PENDING":
        await callback.answer(f"Ushbu so'rov allaqachon yakunlangan ({req['status']})!", show_alert=True)
        return

    target_id = req["target_id"]
    if current_user and current_user["id"] != target_id:
        await callback.answer("Ushbu so'rov sizga yo'naltirilmagan!", show_alert=True)
        return

    payload = json.loads(req["target_info"])
    swap_type = req["swap_type"]
    await SwapRepository.update_swap_status(request_id, "APPROVED")

    if swap_type == "DAILY":
        day_idx = payload["day_idx"]
        target_date = datetime.strptime(payload["target_date_str"], "%Y-%m-%d").date()
        _, week_num, _ = target_date.isocalendar()
        await DutyRepository.set_daily_override(week_num, day_idx, str(target_id))

        requester = await UserRepository.get_user_by_id(req["requester_id"])
        target = await UserRepository.get_user_by_id(req["target_id"])
        success_text = (
            f"✅ <b>KUNLIK NAVBATCHILIK ALMASHIShI TASDIQLANDI!</b>\n\n"
            f"📅 <b>Kun:</b> {payload['day_name']} ({payload['target_date_str']})\n"
            f"🔄 <b>Yangi navbatchi:</b> <b>{target['name']}</b> ({requester['name']} o'rniga)\n\n"
            f"Jadvalga o'zgartirish kiritildi!"
        )
    elif swap_type == "WEEKLY_PAIR":
        month_year = payload["month_year"]
        w1_idx = payload["my_week_idx"]
        w2_idx = payload["target_week_idx"]

        # Swap assignments
        await DutyRepository.set_weekly_pair_assignment(
            month_year, w1_idx, payload["target_pair_id"], payload["target_m1_id"], payload["target_m2_id"]
        )
        await DutyRepository.set_weekly_pair_assignment(
            month_year, w2_idx, payload["my_pair_id"], payload["my_m1_id"], payload["my_m2_id"]
        )

        success_text = (
            f"✅ <b>HAFTALIK JUFTLIK ALMASHIShI TASDIQLANDI!</b>\n\n"
            f"👥 <b>{MONTH_WEEK_NAMES[w1_idx]}:</b> Juftlik #{payload['target_pair_id']}\n"
            f"👥 <b>{MONTH_WEEK_NAMES[w2_idx]}:</b> Juftlik #{payload['my_pair_id']}\n\n"
            f"Oylik reja muvaffaqiyatli yangilandi!"
        )
    elif swap_type == "PAIR_MEMBER_PROXY":
        month_year = payload["month_year"]
        week_idx = payload["week_idx"]
        pair_id = payload["pair_id"]
        other_m_id = payload["other_member_id"]
        proxy_id = payload["proxy_user_id"]

        await DutyRepository.set_weekly_pair_assignment(
            month_year, week_idx, pair_id, other_m_id, proxy_id
        )

        req_u = await UserRepository.get_user_by_id(payload["requester_id"])
        proxy_u = await UserRepository.get_user_by_id(proxy_id)

        success_text = (
            f"✅ <b>O'RINBOSARLIK ALMASHIShI TASDIQLANDI!</b>\n\n"
            f"🗓 <b>Hafta:</b> {MONTH_WEEK_NAMES[week_idx]}\n"
            f"👤 <b>Yangi biriktirilgan a'zo:</b> <b>{proxy_u['name']}</b> ({req_u['name']} o'rniga)\n\n"
            f"Juftlik tarkibi muvaffaqiyatli yangilandi!"
        )
    else:
        success_text = "✅ Almashuv tasdiqlandi!"

    await callback.message.edit_text(success_text, parse_mode="HTML")


@router.callback_query(F.data.startswith("swap_reject:"))
async def callback_reject_swap(callback: CallbackQuery, current_user: dict):
    request_id = callback.data.split(":")[1]
    req = await SwapRepository.get_swap_request(request_id)

    if not req or req["status"] != "PENDING":
        await callback.answer("So'rov topilmadi yoki allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    target_id = req["target_id"]
    if current_user and current_user["id"] != target_id:
        await callback.answer("Ushbu so'rov sizga yo'naltirilmagan!", show_alert=True)
        return

    await SwapRepository.update_swap_status(request_id, "REJECTED")
    target = await UserRepository.get_user_by_id(req["target_id"])

    reject_text = (
        f"❌ <b>NAVBATCHILIK ALMASHIShI RAD ETILDI</b>\n\n"
        f"<b>{target['name']}</b> navbat almashish so'rovini rad etdi."
    )
    await callback.message.edit_text(reject_text, parse_mode="HTML")
