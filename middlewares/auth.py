from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from database.repositories import UserRepository


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        event_user: TgUser = data.get("event_from_user")
        if event_user:
            db_user = await UserRepository.get_user_by_telegram_id(event_user.id)
            data["current_user"] = db_user
        else:
            data["current_user"] = None

        return await handler(event, data)
