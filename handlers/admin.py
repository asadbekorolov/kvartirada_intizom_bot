from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from middlewares.admin import IsAdminFilter
from config import settings
from services.queue_service import ROOM_1_WATER_QUEUE, ROOM_2_WATER_QUEUE, DAY_NAMES, MONTH_WEEK_NAMES
from database.repositories import UserRepository, WaterRepository, DutyRepository, TaskRepository
from utils.cleanup import safe_delete, delete_after

router = Router()
router.message.filter(IsAdminFilter())


@router.message(Command("suv_admin"))
async def cmd_suv_admin(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    args = message.text.split()[1:]
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        msg = await message.answer(
            "⚠️ Foydalanish: <code>/suv_admin &lt;room_id&gt; &lt;user_id&gt;</code>\n"
            "• room_id: 1 (1-xona) yoki 2 (2-xona)\n"
            "• user_id: 1..8 oralig'ida\n"
            "Masalan: <code>/suv_admin 1 3</code> (1-xona suvini Asadbek bro ga o'tkazish)",
            parse_mode="HTML"
        )
        if is_group:
            await delete_after(msg, 30)
        return

    room_id = int(args[0])
    user_id = int(args[1])

    if room_id not in (1, 2):
        msg = await message.answer("❌ Xona raqami faqat 1 yoki 2 bo'lishi mumkin!")
        if is_group:
            await delete_after(msg, 30)
        return

    queue_ids = ROOM_1_WATER_QUEUE if room_id == 1 else ROOM_2_WATER_QUEUE
    if user_id not in queue_ids:
        msg = await message.answer(f"❌ User ID {user_id} {room_id}-xona a'zolari orasida topilmadi! ({queue_ids})")
        if is_group:
            await delete_after(msg, 30)
        return

    user = await UserRepository.get_user_by_id(user_id)
    new_idx = queue_ids.index(user_id)
    await WaterRepository.set_room_water_index(room_id, new_idx)

    msg = await message.answer(
        f"✅ <b>ADMIN:</b> {room_id}-Xona suv navbati majburiy ravishda <b>{user['name']}</b> ga (Index: {new_idx}) o'tkazildi!",
        parse_mode="HTML"
    )
    if is_group:
        await delete_after(msg, 45)


@router.message(Command("almash_admin"))
async def cmd_almash_admin(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    args = message.text.split()[1:]
    if len(args) < 2:
        msg = await message.answer(
            "⚠️ Foydalanish: <code>/almash_admin &lt;day_index&gt; &lt;user_ids&gt;</code>\n"
            "• day_index: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun\n"
            "• user_ids: Masalan <code>2</code> yoki juftlik uchun <code>4,5</code>\n"
            "Misol: <code>/almash_admin 0 2</code>",
            parse_mode="HTML"
        )
        if is_group:
            await delete_after(msg, 30)
        return

    try:
        day_idx = int(args[0])
        user_ids_str = args[1]
    except ValueError:
        msg = await message.answer("❌ Noto'g'ri parametrlar kiritildi.")
        if is_group:
            await delete_after(msg, 30)
        return

    if day_idx < 0 or day_idx > 6:
        msg = await message.answer("❌ Kun indeksi 0 (Dushanba) va 6 (Yakshanba) oralig'ida bo'lishi kerak!")
        if is_group:
            await delete_after(msg, 30)
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

    msg = await message.answer(
        f"✅ <b>ADMIN:</b> <b>{day_name}</b> kungi navbatchilik majburiy ravishda "
        f"<b>{names_str}</b> ga biriktirildi!",
        parse_mode="HTML"
    )
    if is_group:
        await delete_after(msg, 45)


@router.message(Command("pair_admin"))
async def cmd_pair_admin(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    args = message.text.split()[1:]
    if len(args) < 4:
        msg = await message.answer(
            "⚠️ Foydalanish: <code>/pair_admin &lt;week_idx_0_to_3&gt; &lt;pair_id&gt; &lt;user1_id&gt; &lt;user2_id&gt;</code>\n"
            "Misol: <code>/pair_admin 0 1 4 3</code>",
            parse_mode="HTML"
        )
        if is_group:
            await delete_after(msg, 30)
        return

    week_idx = int(args[0])
    pair_id = int(args[1])
    m1_id = int(args[2])
    m2_id = int(args[3])

    today = datetime.now(settings.timezone).date()
    month_year = today.strftime("%Y-%m")

    await DutyRepository.set_weekly_pair_assignment(month_year, week_idx, pair_id, m1_id, m2_id)
    u1 = await UserRepository.get_user_by_id(m1_id)
    u2 = await UserRepository.get_user_by_id(m2_id)

    msg = await message.answer(
        f"✅ <b>ADMIN:</b> <b>{MONTH_WEEK_NAMES[week_idx]}</b> juftligi majburiy ravishda "
        f"<b>{u1['name']} & {u2['name']}</b> (Juftlik #{pair_id}) ga biriktirildi!",
        parse_mode="HTML"
    )
    if is_group:
        await delete_after(msg, 45)


@router.message(Command("reset_tasks"))
async def cmd_reset_tasks(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    today = datetime.now(settings.timezone).date()
    today_str = today.strftime("%Y-%m-%d")

    await TaskRepository.reset_daily_tasks(today_str)
    msg = await message.answer(
        f"✅ Bugungi ({today_str}) kunlik vazifalar holatlari tozalandi!",
        parse_mode="HTML"
    )
    if is_group:
        await delete_after(msg, 30)


@router.message(Command("bind_admin"))
async def cmd_bind_admin(message: Message):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group:
        await safe_delete(message)

    args = message.text.split()[1:]
    if len(args) < 2 or not args[0].isdigit() or not args[1].isdigit():
        msg = await message.answer(
            "⚠️ Foydalanish: <code>/bind_admin &lt;user_id&gt; &lt;telegram_id&gt;</code>\n"
            "Misol: <code>/bind_admin 1 123456789</code>",
            parse_mode="HTML"
        )
        if is_group:
            await delete_after(msg, 30)
        return

    user_id = int(args[0])
    tg_id = int(args[1])

    user = await UserRepository.get_user_by_id(user_id)
    if not user:
        msg = await message.answer("❌ Bunday user ID topilmadi!")
        if is_group:
            await delete_after(msg, 30)
        return

    await UserRepository.bind_telegram_id(user_id, tg_id)
    msg = await message.answer(
        f"✅ <b>{user['name']}</b> profiliga Telegram ID <code>{tg_id}</code> biriktirildi!",
        parse_mode="HTML"
    )
    if is_group:
        await delete_after(msg, 30)
