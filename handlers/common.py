from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.repositories import UserRepository
from keyboards.reply import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, current_user: dict):
    tg_id = message.from_user.id
    name = message.from_user.full_name

    text = (
        f"👋 <b>Assalomu alaykum, {name}!</b>\n\n"
        f"🏢 <b>Kvartira Bot</b> tizimiga xush kelibsiz!\n"
        f"Ushbu bot 8 kishilik xonadonimizdagi kunlik navbatchilik, kir yuvish, "
        f"suv keltirish va general uborqa jarayonlarini avtomatlashtirish uchun xizmat qiladi.\n\n"
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
    text = (
        "ℹ️ <b>KVARTIRA BOT — YO'RIQNOMA VA BUYRUQLAR</b>\n\n"
        "<b>📱 Asosiy Tugmalar:</b>\n"
        "• 📋 <b>Bugungi navbatchilik:</b> Bugungi kunlik navbatchi, kir yuvish va suv navbatini ko'rish hamda vazifalarni belgilash.\n"
        "• 🚰 <b>Suv olib keldim:</b> Suv keltirganda rasm isbotini yuborib navbatni keyingi kishiga o'tkazish.\n"
        "• 🔄 <b>Navbat almashish:</b> Kunlik navbatchilikni boshqa xonadosh bilan almashish so'rovini yuborish.\n\n"
        "<b>⚙️ Admin Buyruqlari (Faqat adminlar uchun):</b>\n"
        "• <code>/suv_admin &lt;user_id&gt;</code> - Suv navbatini ko'rsatilgan kishiga majburiy o'tkazish (1..8).\n"
        "• <code>/almash_admin &lt;day_idx&gt; &lt;user_ids&gt;</code> - Kunlik navbatchilikni majburiy o'zgartirish (masalan: <code>/almash_admin 0 2</code>).\n"
        "• <code>/reset_tasks</code> - Bugungi vazifalar holatini qayta tiklash.\n"
        "• <code>/bind_admin &lt;user_id&gt; &lt;telegram_id&gt;</code> - Profilni Telegram ID ga majburiy bog'lash.\n"
    )
    await message.answer(text, parse_mode="HTML")
