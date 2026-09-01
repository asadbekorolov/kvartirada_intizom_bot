from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from middlewares.admin import IsAdminFilter
from config import settings
from services.queue_service import WATER_QUEUE_IDS, DAY_NAMES
from database.repositories import UserRepository, WaterRepository, DutyRepository, TaskRepository

router = Router()
router.message.filter(IsAdminFilter())


@router.message(Command("suv_admin"))
async def cmd_suv_admin(message: Message):
    args = message.text.split()[1:]
    if not args or not args[0].isdigit():
        await message.answer(
            "⚠️ Foydalanish: <code>/suv_admin &lt;user_id&gt;</code> (1..8 oralig'ida)\n"
            "Masalan: <code>/suv_admin 3</code> (Asadbek bro uchun)",
            parse_mode="HTML"
        )
        return

    user_id = int(args[0])
    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        await message.answer("❌ Bunday user ID topilmadi! (1..8 oralig'ida bo'lishi kerak)")
        return

    if user_id in WATER_QUEUE_IDS:
        new_idx = WATER_QUEUE_IDS.index(user_id)
    else:
        new_idx = 0

    await WaterRepository.set_current_water_index(new_idx)
    await message.answer(
        f"✅ <b>ADMIN BUYRUG'I:</b> Suv navbati majburiy ravishda <b>{user['name']}</b> ga (Index: {new_idx}) o'tkazildi!",
        parse_mode="HTML"
    )


@router.message(Command("almash_admin"))
async def cmd_almash_admin(message: Message):
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer(
            "⚠️ Foydalanish: <code>/almash_admin &lt;day_index&gt; &lt;user_ids&gt;</code>\n"
            "• day_index: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun\n"
            "• user_ids: Masalan <code>2</code> yoki juftlik uchun <code>4,5</code>\n"
            "Misol: <code>/almash_admin 0 2</code>",
            parse_mode="HTML"
        )
        return

    try:
        day_idx = int(args[0])
        user_ids_str = args[1]
    except ValueError:
        await message.answer("❌ Noto'g me'yorlar kiritildi.")
        return

    if day_idx < 0 or day_idx > 6:
        await message.answer("❌ Kun indeksi 0 (Dushanba) va 6 (Yakshanba) oralig'ida bo'lishi kerak!")
        return

    today = datetime.now(settings.timezone).date()
    _, week_num, _ = today.isocalendar()

    await DutyRepository.set_daily_override(week_num, day_idx, user_ids_str)
    day_name = DAY_NAMES[day_idx]

    user_ids = [int(x.strip()) for x in user_ids_str.split(",") if x.strip()]
    user_names = []
    for uid in user_ids:
        u = await UserRepository.get_user_by_id(uid)
        if u:
            user_names.append(u['name'])
    names_str = ", ".join(user_names)

    await message.answer(
        f"✅ <b>ADMIN BUYRUG'I:</b> <b>{day_name}</b> kungi navbatchilik majburiy ravishda "
        f"<b>{names_str}</b> ga biriktirildi!",
        parse_mode="HTML"
    )


@router.message(Command("reset_tasks"))
async def cmd_reset_tasks(message: Message):
    today = datetime.now(settings.timezone).date()
    today_str = today.strftime("%Y-%m-%d")

    await TaskRepository.reset_daily_tasks(today_str)
    await message.answer(
        f"✅ Bugungi ({today_str}) kunlik vazifalar ro'yxati va holatlari tozalandi!",
        parse_mode="HTML"
    )


@router.message(Command("bind_admin"))
async def cmd_bind_admin(message: Message):
    args = message.text.split()[1:]
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        await message.answer(
            "⚠️ Foydalanish: <code>/bind_admin &lt;user_id&gt; &lt;telegram_id&gt;</code>\n"
            "Misol: <code>/bind_admin 1 123456789</code>",
            parse_mode="HTML"
        )
        return

    user_id = int(args[0])
    tg_id = int(args[1])

    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        await message.answer("❌ Bunday user ID topilmadi!")
        return

    await UserRepository.bind_telegram_id(user_id, tg_id)
    await message.answer(
        f"✅ <b>{user['name']}</b> profiliga Telegram ID <code>{tg_id}</code> biriktirildi!",
        parse_mode="HTML"
    )
