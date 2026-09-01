from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import WaterStates
from services.queue_service import QueueService
from database.repositories import UserRepository
from keyboards.inline import build_water_bringer_keyboard

router = Router()


@router.message(Command("suv"))
@router.message(F.text == "🚰 Suv olib keldim")
async def cmd_water_start(message: Message, state: FSMContext):
    users = await UserRepository.get_all_users()
    keyboard = build_water_bringer_keyboard(users)
    await state.set_state(WaterStates.waiting_for_bringer)
    await message.answer(
        "🚰 <b>Suv olib kelish navbatini qayd etish</b>\n\n"
        "Suvni kim olib keldi? Iltimos, pastdagi ro'yxatdan tanlang:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("water_bringer:"), WaterStates.waiting_for_bringer)
async def callback_select_water_bringer(callback: CallbackQuery, state: FSMContext):
    bringer_id = int(callback.data.split(":")[1])
    bringer = await UserRepository.get_user_by_id(bringer_id)

    if not bringer:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await state.update_data(bringer_id=bringer_id)
    await state.set_state(WaterStates.waiting_for_photo_proof)

    await callback.message.edit_text(
        f"📸 <b>Rasm isboti kutilmoqda...</b>\n\n"
        f"Tanlandi: <b>{bringer['name']}</b>\n"
        f"Iltimos, idishlar va suv rasm proof ini (Foto) ushbu chatga yuboring:",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "water_cancel")
async def callback_cancel_water(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Suv olib kelish operatsiyasi bekor qilindi.")


@router.message(WaterStates.waiting_for_photo_proof, F.photo)
async def process_water_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    bringer_id = data.get("bringer_id")

    if not bringer_id:
        await message.answer("Xatolik yuz berdi. Iltimos, qaytadan /suv buyrug'ini bosing.")
        await state.clear()
        return

    photo_file_id = message.photo[-1].file_id
    result = await QueueService.record_water_delivery(bringer_id, photo_file_id)

    brought_by = result["brought_by"]
    next_user = result["next_user"]

    next_tag = f"<b>{next_user['name']}</b>"
    if next_user.get("telegram_id"):
        next_tag = f"<a href='tg://user?id={next_user['telegram_id']}'>{next_user['name']}</a>"

    caption = (
        f"✅ <b>SUV KELTIRILGANI TASDIQLANDI!</b> 🚰\n\n"
        f"👤 <b>Suv olib keldi:</b> {brought_by['name']} (Xona {brought_by['room_number']})\n"
        f"➡️ <b>Keyingi suv navbati:</b> {next_tag}\n\n"
        f"Baraka topsin! Keyingi navbatdagi xonadoshimiz tayyor tursin! 👍"
    )

    await message.answer_photo(
        photo=photo_file_id,
        caption=caption,
        parse_mode="HTML"
    )
    await state.clear()


@router.message(WaterStates.waiting_for_photo_proof)
async def process_water_photo_invalid(message: Message):
    await message.answer("⚠️ Iltimos, suv olib kelingani isboti sifatida <b>Foto (Rasm)</b> yuboring!", parse_mode="HTML")
