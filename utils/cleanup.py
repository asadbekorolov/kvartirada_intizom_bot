import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from database.repositories import MessageDeletionRepository

logger = logging.getLogger("kvartira_bot.cleanup")

GROUP_MESSAGE_LIFETIME_SECONDS = 6 * 3600  # 6 hours = 21,600 seconds


async def safe_delete_message(bot: Bot, chat_id: int, message_id: int):
    """Safely attempts to delete a message by chat_id and message_id."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug(f"Deleted message {message_id} in chat {chat_id}")
    except Exception as e:
        logger.debug(f"Could not delete message {message_id} in {chat_id}: {e}")


async def safe_delete(message: Message):
    """Safely attempts to delete a Message object."""
    if not message:
        return
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete message {getattr(message, 'message_id', '?')}: {e}")


async def delete_after(message: Message, delay: int = 30):
    """Asynchronously deletes a message after a given delay in seconds."""
    async def _worker():
        await asyncio.sleep(delay)
        await safe_delete(message)
    
    asyncio.create_task(_worker())


async def schedule_group_message_deletion(
    bot: Bot,
    message: Message,
    delay_seconds: int = GROUP_MESSAGE_LIFETIME_SECONDS
):
    """
    Schedules a group message to be deleted after delay_seconds (default 6 hours).
    Stores deletion in DB to survive bot restarts, and launches an in-memory timer.
    """
    if not message or not message.chat:
        return

    chat_id = message.chat.id
    message_id = message.message_id
    delete_at = datetime.now() + timedelta(seconds=delay_seconds)
    delete_at_iso = delete_at.isoformat()

    try:
        await MessageDeletionRepository.schedule_deletion(chat_id, message_id, delete_at_iso)
    except Exception as e:
        logger.warning(f"Failed to persist message deletion in DB ({chat_id}:{message_id}): {e}")

    async def _wait_and_delete():
        try:
            await asyncio.sleep(delay_seconds)
            await safe_delete_message(bot, chat_id, message_id)
            await MessageDeletionRepository.remove_deletion(chat_id, message_id)
        except Exception as err:
            logger.debug(f"In-memory deletion failed ({chat_id}:{message_id}): {err}")

    asyncio.create_task(_wait_and_delete())


async def process_due_message_deletions(bot: Bot):
    """
    Checks the database for any message deletions that have reached their expiry time
    (e.g., messages sent 6 hours ago that weren't deleted due to bot downtime).
    """
    now_iso = datetime.now().isoformat()
    try:
        due_items = await MessageDeletionRepository.get_due_deletions(now_iso)
        if due_items:
            logger.info(f"Found {len(due_items)} expired group messages to delete.")
        for item in due_items:
            chat_id = item["chat_id"]
            message_id = item["message_id"]
            await safe_delete_message(bot, chat_id, message_id)
            await MessageDeletionRepository.remove_deletion(chat_id, message_id)
    except Exception as e:
        logger.error(f"Error processing due message deletions: {e}")
