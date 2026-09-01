import asyncio
import logging
from aiogram.types import Message

logger = logging.getLogger("kvartira_bot.cleanup")


async def safe_delete(message: Message):
    """Safely attempts to delete a message without raising exceptions."""
    try:
        await message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete message {message.message_id}: {e}")


async def delete_after(message: Message, delay: int = 30):
    """Asynchronously deletes a message after a given delay in seconds."""
    async def _worker():
        await asyncio.sleep(delay)
        await safe_delete(message)
    
    asyncio.create_task(_worker())
