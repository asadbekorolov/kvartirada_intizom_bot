from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from database.repositories import UserRepository, SettingsRepository
from keyboards.reply import get_main_reply_keyboard
from utils.cleanup import safe_delete, delete_after, schedule_group_message_deletion
from services.notifier import send_morning_brief_to_group, broadcast_change


router = Router()


async def get_claim_keyboard() -> InlineKeyboardMarkup:
    users = await UserRepository.get_all_users()
    buttons = []
    for u in users:
        if u["id"] == 4:  # Omadbek navbatchilikdan chiqarilgan
            continue
        if not u.get("telegram_id"):
            buttons.append([InlineKeyboardButton(text=f"👤 Men {u['name']}man (Xona {u['room_number']})", callback_data=f"claim_user:{u['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
    elif payload == "unbind":
        await UserRepository.unbind_user_by_telegram_id(message.from_user.id)
        current_user = None

    name = message.from_user.full_name
    text = (
        f"👋 <b>Assalomu alaykum, {name}!</b>\n\n"
        f"🏢 <b>Kvartira Bot</b> tizimiga xush kelibsiz!\n"
        f"Ushbu bot 8 kishilik xonadonimizdagi kunlik navbatchilik, kir yuvish, "
        f"2 ta xona baki suvini keltirish, bozorlik va general uborqa jarayonlarini boshqaradi.\n\n"
    )

    if current_user:
        text += f"✅ Siz tizimda <b>{current_user['name']}</b> (Xona {current_user['room_number']}) sifatida bog'langansiz."
        reselect_kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔄 Profilni qayta tanlash / Unbind", callback_data="reselect_profile")
        ]])
        await message.answer(text, reply_markup=get_main_reply_keyboard(), parse_mode="HTML")
        await message.answer("Agar profilingiz xato tanlangan bo'lsa, quyidagi tugmani bosing:", reply_markup=reselect_kb)
    else:
        text += "⚠️ Sizning Telegram hisobingiz hali xonadondagi profilingizga bog'lanmagan. Iltimos, ismingizni tanlang:"
        kb = await get_claim_keyboard()
        # Always send bottom reply keyboard first to refresh client UI
        await message.answer("Quyidagi menyu orqali bot imkoniyatlaridan foydalanishingiz mumkin:", reply_markup=get_main_reply_keyboard())
        if not kb.inline_keyboard:
            text += "\n\n(Barcha 8 ta profil bog'lab bo'lingan. Admin yordamida o'zgartirishingiz mumkin.)"
            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(Command("unbind"))
@router.message(Command("qayta_tanlash"))
@router.message(F.text == "🔄 Profilni qayta tanlash / Unbind")
async def cmd_unbind(message: Message):
    is_group = message.chat.type in ("group", "supergroup")

    if is_group:
        await safe_delete(message)

    await UserRepository.unbind_user_by_telegram_id(message.from_user.id)
    kb = await get_claim_keyboard()

    text = (
        "🔄 <b>Profilingiz uzildi (Unbind qilindi).</b>\n\n"
        "Iltimos, o'zingizga tegishli haqiqiy profilingizni tanlang:"
    )

    if is_group:
        msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        await delete_after(msg, 45)
    else:
        await message.answer("Menyu yangilandi:", reply_markup=get_main_reply_keyboard())
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "reselect_profile")
async def callback_reselect_profile(callback: CallbackQuery):
    await UserRepository.unbind_user_by_telegram_id(callback.from_user.id)
    kb = await get_claim_keyboard()
    await callback.message.answer("Menyu yangilandi:", reply_markup=get_main_reply_keyboard())
    await callback.message.edit_text(
        "🔄 <b>Profilingiz uzildi.</b>\n\nIltimos, o'zingizning haqiqiy profilingizni tanlang:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("claim_user:"))
async def callback_claim_user(callback: CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    tg_id = callback.from_user.id
    
    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    if user.get("telegram_id") and user.get("telegram_id") != tg_id:
        await callback.answer("Ushbu profil allaqachon boshqa foydalanuvchiga bog'langan!", show_alert=True)
        return

    # First unbind any previous profile bound to this telegram_id
    await UserRepository.unbind_user_by_telegram_id(tg_id)
    await UserRepository.bind_telegram_id(user_id, tg_id)
    
    await callback.message.edit_text(
        f"🎉 Tabriklaymiz! Siz muvaffaqiyatli <b>{user['name']}</b> (Xona {user['room_number']}) profili bilan bog'landingiz!",
        parse_mode="HTML"
    )
    await callback.message.answer("Asosiy menyu faollashtirildi:", reply_markup=get_main_reply_keyboard())

    # Broadcast new flatmate connection to the group
    await broadcast_change(
        bot=callback.bot,
        title="Yangi a'zo ulandi",
        details=f"👤 <b>{user['name']}</b> (Xona {user['room_number']}) o'zining Telegram hisobini botga muvaffaqiyatli bog'ladi!",
        icon="👋"
    )


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, bot: Bot):
    if event.chat.type in ("group", "supergroup"):
        if event.new_chat_member.status in ("member", "administrator"):
            await SettingsRepository.set_group_chat_id(event.chat.id)
            welcome_text = (
                "🏢 <b>Assalomu alaykum, hurmatli xonadoshlar!</b>\n\n"
                "<b>Kvartira Intizom Boti</b> ushbu guruhga muvaffaqiyatli ulandi!\n\n"
                "📢 <b>Bot ushbu guruhga quyidagi xabarlarni yuborib turadi:</b>\n"
                "• ☀️ <b>Har kuni ertalab (07:30):</b> Kunlik navbatchi, kir yuvish, suv navbati va vazifalar checklisti;\n"
                "• 🔄 <b>O'zgarishlar:</b> Vazifalar bajarilishi, suv olib kelinishi, navbat almashuvlari va admin yangilanishlari;\n"
                "• 🚨 <b>Kechki eslatma (21:30):</b> Axlat to'kish nazorati;\n"
                "• 🧹 <b>Yakshanba (09:00):</b> General tozalik brifingi.\n\n"
                "💡 <i>Ertalabki xabarni hoziroq ko'rish uchun:</i> /ertalab yoki /bugun\n"
                "⚙️ <i>Guruhni qayta ulash uchun:</i> /guruh_ulash"
            )
            welcome_msg = await bot.send_message(event.chat.id, welcome_text, parse_mode="HTML")
            await schedule_group_message_deletion(bot, welcome_msg)


@router.message(Command("set_group", "guruh_ulash"))
async def cmd_set_group(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("⚠️ Ushbu buyruq faqat xonadon guruhida berilishi kerak!")
        return
    await SettingsRepository.set_group_chat_id(message.chat.id)
    confirm_msg = await message.answer(
        "✅ <b>Guruh muvaffaqiyatli ulandi!</b>\n\n"
        f"Ushbu guruh (ID: <code>{message.chat.id}</code>) bot uchun rasmiy bildirishnoma guruhi qilib belgilandi.\n"
        "Endi barcha ertalabki eslatmalar va tizimdagi o'zgarishlar shu yerga yuboriladi.",
        parse_mode="HTML"
    )
    await schedule_group_message_deletion(message.bot, confirm_msg)



@router.message(Command("ertalab", "eslatma"))
async def cmd_send_morning(message: Message, bot: Bot):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await SettingsRepository.set_group_chat_id(message.chat.id)
        await send_morning_brief_to_group(bot, chat_id=message.chat.id)
    else:
        success = await send_morning_brief_to_group(bot)
        if success:
            await message.answer("✅ Ertalabki brifing guruhga yuborildi!")
        else:
            await message.answer("⚠️ Guruh chat ID topilmadi. Botni avval guruhga qo'shib /guruh_ulash buyrug'ini yuboring.")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    text = (
        "ℹ️ <b>KVARTIRA BOT — YO'RIQNOMA VA QOIDALAR</b>\n\n"
        "<b>📅 Kunlik Navbatchilik Tartibi:</b>\n"
        "• Dushanba: Jaloliddin\n"
        "• Seshanba: Asadbek bro\n"
        "• Chorshanba: Asadbek (men)\n"
        "• Payshanba: Firdavs\n"
        "• Juma: Mavlonbek\n"
        "• Shanba: Avazbek\n"
        "• Yakshanba: Ilyosbek\n\n"
        "<b>🚰 Suv Navbati Tartibi:</b>\n"
        "• 🏠 <b>1-Xona (10L Baklashka):</b> Faqat Avazbek va Firdavs navbatma-navbat olib keladi.\n"
        "• 🚪 <b>2-Xona (Baki):</b> Asadbek, Jaloliddin, Mavlonbek 2 martadan, Ilyosbek esa 1 marta olib keladi.\n"
        "<i>(Suv keltirilgach rasm proof yuboriladi va navbat aylanadi.)</i>\n\n"
        "<b>👥 Oylik 4-Haftalik Juftliklar (Uborqa & Bozorlik):</b>\n"
        "• 1-hafta (1–7 kunlar): Asadbek bro & Jaloliddin\n"
        "• 2-hafta (8–14 kunlar): Avazbek & Firdavs\n"
        "• 3-hafta (15–21 kunlar): Mavlonbek & Asadbek\n"
        "• 4-hafta (22–oy oxiri): Ilyosbek & Asadbek bro\n\n"
        "<b>🔄 Navbat Almashish (/almashish):</b>\n"
        "• Kunlik navbatchilik, butun haftalik juftlik yoki juftlik ichida alohida o'rinbosar almashish imkoniyati.\n\n"
        "<b>🔔 Guruh xabarlari:</b>\n"
        "• <code>/ertalab</code> yoki <code>/bugun</code> — Ertalabki brifingni darhol ko'rish.\n"
        "• <code>/guruh_ulash</code> — Guruhni rasmiy eslatmalar guruhi qilib belgilash.\n"
        "• <code>/unbind</code> yoki <code>/qayta_tanlash</code> — Profilingizni bekor qilib yangitdan tanlash.\n"
    )
    
    if is_group:
        msg = await message.answer(text, parse_mode="HTML")
        await delete_after(msg, 45)
    else:
        await message.answer(text, reply_markup=get_main_reply_keyboard(), parse_mode="HTML")

