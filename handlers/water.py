from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states import WaterStates
from config import settings
from services.queue_service import QueueService
from database.repositories import UserRepository
from keyboards.inline import build_water_room_keyboard, build_water_bringer_keyboard
from utils.cleanup import safe_delete, delete_after
from services.notifier import send_group_message

router = Router()


async def start_water_flow_for_room(message: Message, room_id: int, state: FSMContext = None):
    users = await UserRepository.get_users_by_room(room_id)
    keyboard = build_water_bringer_keyboard(users, room_id)
    if state:
        await state.set_state(WaterStates.waiting_for_bringer)
        await state.update_data(room_id=room_id)
    await message.answer(
        f"🚰 <b>{room_id}-Xona Baki: Suv keltirish</b>\n\n"
        f"Suvni kim olib keldi? Quyidagi ro'yxatdan tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("suv"))
@router.message(F.text == "🚰 Suv olib keldim")
async def cmd_water_start(message: Message, state: FSMContext, bot: Bot):
    # If in group, redirect to PM to avoid chat clutter
    if message.chat.type in ("group", "supergroup"):
        await safe_delete(message)
        me = await bot.get_me()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 1-Xona Suvi (PM)", url=f"https://t.me/{me.username}?start=water_r1"),
                InlineKeyboardButton(text="🚪 2-Xona Suvi (PM)", url=f"https://t.me/{me.username}?start=water_r2"),
            ]
        ])
        msg = await message.answer(
            "🚰 <b>Suv olib kelishni qayd etish</b>\n\n"
            "Guruhda ortiqcha xabar to'planmasligi uchun iltimos, botning shaxsiy chatiga o'ting:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await delete_after(msg, 30)
        return

    # In PM:
    await state.set_state(WaterStates.waiting_for_room)
    await message.answer(
        "🚰 <b>Suv olib kelish navbatini qayd etish</b>\n\n"
        "Qaysi xona baki uchun suv keltirildi?",
        reply_markup=build_water_room_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("water_room:"))
async def callback_select_water_room(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split(":")[1])
    users = await UserRepository.get_users_by_room(room_id)
    keyboard = build_water_bringer_keyboard(users, room_id)

    await state.set_state(WaterStates.waiting_for_bringer)
    await state.update_data(room_id=room_id)

    await callback.message.edit_text(
        f"🚰 <b>{room_id}-Xona Baki: Suv keltirish</b>\n\n"
        f"Suvni kim olib keldi? Quyidagi ro'yxatdan tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "water_back_room")
async def callback_water_back_room(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WaterStates.waiting_for_room)
    await callback.message.edit_text(
        "🚰 <b>Suv olib kelish navbatini qayd etish</b>\n\n"
        "Qaysi xona baki uchun suv keltirildi?",
        reply_markup=build_water_room_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "water_cancel")
async def callback_cancel_water(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Suv olib kelish operatsiyasi bekor qilindi.")


@router.callback_query(F.data.startswith("water_bringer:"))
async def callback_select_water_bringer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    room_id = int(parts[1])
    bringer_id = int(parts[2])

    bringer = await UserRepository.get_user_by_id(bringer_id)
    if not bringer:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await state.update_data(room_id=room_id, bringer_id=bringer_id)
    await state.set_state(WaterStates.waiting_for_photo_proof)

    await callback.message.edit_text(
        f"📸 <b>Rasm isboti kutilmoqda...</b>\n\n"
        f"🏠 <b>Xona:</b> {room_id}-xona baki\n"
        f"👤 <b>Keltiruvchi:</b> {bringer['name']}\n\n"
        f"Iltimos, keltirilgan suv idishi (bak) rasm proof ini (Foto) ushbu bot chatiga yuboring:",
        parse_mode="HTML"
    )


@router.message(WaterStates.waiting_for_photo_proof, F.photo)
async def process_water_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    room_id = data.get("room_id", 1)
    bringer_id = data.get("bringer_id")

    if not bringer_id:
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan /suv buyrug'ini bosing.")
        await state.clear()
        return

    photo_file_id = message.photo[-1].file_id
    result = await QueueService.record_room_water_delivery(room_id, bringer_id, photo_file_id)

    brought_by = result["brought_by"]
    next_user = result["next_user"]

    next_tag = f"<b>{next_user['name']}</b>"
    if next_user.get("telegram_id"):
        next_tag = f"<a href='tg://user?id={next_user['telegram_id']}'>{next_user['name']}</a>"

    # Confirmation to user in PM
    await message.answer_photo(
        photo=photo_file_id,
        caption=(
            f"✅ <b>{room_id}-XONA BAKI: SUV QAYD ETILDI!</b> 🚰\n\n"
            f"👤 <b>Keltirdi:</b> {brought_by['name']}\n"
            f"➡️ <b>Keyingi navbatchi:</b> {next_tag}\n\n"
            f"Guruhga xabar yuborildi. Rahmat! 👍"
        ),
        parse_mode="HTML"
    )

    # Post exactly ONE clean notification to the main group chat
    group_caption = (
        f"✅ <b>{room_id}-XONA BAKI: SUV KELTIRILDI!</b> 🚰\n\n"
        f"👤 <b>Suv olib keldi:</b> {brought_by['name']} (Xona {room_id})\n"
        f"➡️ <b>Keyingi navbatdagi:</b> {next_tag}\n\n"
        f"Baraka topsin! Navbatdagi xonadoshimiz tayyor tursin! 💧👏"
    )

    await send_group_message(
        bot=bot,
        text=group_caption,
        photo=photo_file_id
    )

    await state.clear()



@router.message(WaterStates.waiting_for_photo_proof)
async def process_water_photo_invalid(message: Message):
    await message.answer("⚠️ Iltimos, suv olib kelingani isboti sifatida <b>Foto (Rasm)</b> yuboring!", parse_mode="HTML")
