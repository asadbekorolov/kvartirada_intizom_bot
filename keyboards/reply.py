from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    # Row 1
    builder.button(text="📋 Bugungi navbatchilik")
    builder.button(text="🗓 Haftalik navbatchilik (Bozorlik)")
    # Row 2
    builder.button(text="🚰 Suv olib keldim")
    builder.button(text="🔄 Navbat almashish")
    # Row 3
    builder.button(text="🔄 Profilni qayta tanlash / Unbind")
    builder.button(text="ℹ️ Yordam")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)
