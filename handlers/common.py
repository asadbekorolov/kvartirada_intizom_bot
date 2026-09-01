from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repositories import UserRepository
from keyboards.reply import main_menu_keyboard
from utils.cleanup import safe_delete, delete_after

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, current_user: dict, bot: Bot):
    if message.chat.type in ("group", "supergroup"):
        await safe_delete(message)
        me = await bot.get_me()
        btn = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="💬 Botga o'tish (PM)", url=f"https://t.me/{me.username}?start=help")
        ]])
        msg = await message.answer("ℹ️ Bot bilan ishlash uchun shaxsiy xabarga (PM) o'ting:", reply_markup=btn)
        await delete_after(msg, 30)
        return

    payload = command.args if command else None

    # Handle Deep Links
    if payload == "water_r1":
        from handlers.water import start_water_flow_for_room
        await start_water_flow_for_room(message, room_id=1)
        return
    elif payload == "water_r2":
        from handlers.water import start_water_flow_for_room
        await start_water_flow_for_room(message, room_id=2)
        return
    elif payload == "swap":
        from handlers.swap import start_swap_flow_pm
        await start_swap_flow_pm(message, current_user)
        return

    name = message.from_user.full_name
    text = (
        f"👋 <b>Assalomu alaykum, {name}!</b>\n\n"
        f"🏢 <b>Kvartira Bot</b> tizimiga xush kelibsiz!\n"
        f"Ushbu bot 8 kishilik xonadonimizdagi kunlik navbatchilik, kir yuvish, "
        f"2 ta xona baki suvini keltirish, bozorlik va general uborqa jarayonlarini boshqaradi.\n\n"
    )

    if current_user:
        text += f"✅ Siz tizimda <b>{current_user['name']}</b> (Xona {current_user['room_number']}) sifatida bog'langansiz."
        await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
    else:
        text += "⚠️ Sizning Telegram hisobingiz hali xonadondagi profilingizga bog'lanmagan. Iltimos, ismingizni tanlang:"
        users = await UserRepository.get_all_users()
        buttons = []
        for u in users:
            if not u.get("telegram_id"):
                buttons.append([InlineKeyboardButton(text=f"👤 Men {u['name']}man (Xona {u['room_number']})", callback_data=f"claim_user:{u['id']}")])
        
        if not buttons:
            text += "\n\n(Barcha 8 ta profil bog'lab bo'lingan. Admin yordamida o'zgartirishingiz mumkin.)"
            await message.answer(text, reply_markup=main_menu_keyboard(), parse_mode="HTML")
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("claim_user:"))
async def callback_claim_user(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    tg_id = callback.from_user.id
    
    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if user.get("telegram_id"):
        await callback.answer("Ushbu profil allaqachon boshqa foydalanuvchiga bog'langan!", show_alert=True)
        return

    await UserRepository.bind_telegram_id(user_id, tg_id)
    await callback.message.edit_text(
        f"🎉 Tabriklaymiz! Siz muvaffaqiyatli <b>{user['name']}</b> (Xona {user['room_number']}) profili bilan bog'landindingiz!",
        parse_mode="HTML"
    )
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    text = (
        "ℹ️ <b>KVARTIRA BOT — YO'RIQNOMA VA QOIDALAR</b>\n\n"
        "<b>🚰 Suv Navbati (2 ta Alohida Bak):</b>\n"
        "• 🏠 <b>1-Xona Baki:</b> Avazbek ➔ Firdavs ➔ Asadbek bro ➔ Omadbek\n"
        "• 🚪 <b>2-Xona Baki:</b> Ilyosbek ➔ Jaloliddin ➔ Asadbek ➔ Mavlonbek\n"
        "<i>(Suv keltirilgach rasm proof yuboriladi va navbat aylanadi.)</i>\n\n"
        "<b>👥 Oylik 4-Haftalik Juftliklar (Uborqa & Bozorlik):</b>\n"
        "• 1-hafta (1–7 kunlar): Omadbek & Asadbek bro\n"
        "• 2-hafta (8–14 kunlar): Ilyosbek & Jaloliddin\n"
        "• 3-hafta (15–21 kunlar): Avazbek & Firdavs\n"
        "• 4-hafta (22–oy oxiri): Mavlonbek & Asadbek\n\n"
        "<b>🔄 Navbat Almashish (/almashish):</b>\n"
        "• Kunlik navbatchilik, butun haftalik juftlik yoki juftlik ichida alohida o'rinbosar almashish imkoniyati.\n"
    )
    
    msg = await message.answer(text, parse_mode="HTML")
    if is_group:
        await delete_after(msg, 45)
