from typing import Callable, Dict, Any, Awaitable
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery, User as TgUser
from config import settings
from database.repositories import UserRepository


class IsAdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user: TgUser = event.from_user
        if not user:
            return False

        if user.id in settings.admin_user_ids_list:
            return True

        db_user = await UserRepository.get_user_by_telegram_id(user.id)
        if db_user and db_user.get("is_admin"):
            return True

        return False

