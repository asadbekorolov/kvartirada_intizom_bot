from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser, Chat as TgChat
from database.repositories import UserRepository, SettingsRepository


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

        event_chat: TgChat = data.get("event_chat")
        if event_chat and event_chat.type in ("group", "supergroup"):
            # Auto-register group chat if not set yet
            current_saved_group = await SettingsRepository.get_setting("group_chat_id")
            if not current_saved_group:
                await SettingsRepository.set_group_chat_id(event_chat.id)

        return await handler(event, data)
