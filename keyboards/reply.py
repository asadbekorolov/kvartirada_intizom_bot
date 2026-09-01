from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🚰 Suv olib keldim")
    builder.button(text="📋 Bugungi navbatchilik")
    builder.button(text="🔄 Navbat almashish")
    builder.button(text="ℹ️ Yordam")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)
