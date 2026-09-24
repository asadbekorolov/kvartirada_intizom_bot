import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from database.connection import init_db
from middlewares.auth import AuthMiddleware
from services.scheduler_jobs import setup_scheduler
from services.web_server import start_web_server
from utils.cleanup import process_due_message_deletions
from handlers import common, duty, water, swap, admin



async def main():
    # 1. Setup Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger("kvartira_bot")
    logger.info("Starting Kvartira Bot initialization...")

    # 2. Initialize Database & Seed Data
    await init_db()
    logger.info("Database initialized successfully.")

    # 3. Create Bot and Dispatcher Instances
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    # 4. Attach Middlewares
    auth_middleware = AuthMiddleware()
    dp.message.outer_middleware(auth_middleware)
    dp.callback_query.outer_middleware(auth_middleware)

    # 5. Include Handlers Routers
    dp.include_router(common.router)
    dp.include_router(duty.router)
    dp.include_router(water.router)
    dp.include_router(swap.router)
    dp.include_router(admin.router)

    # 6. Setup and Start APScheduler (Asia/Tashkent)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info("APScheduler started with Tashkent timezone jobs.")

    # Process any overdue message deletions from previous downtime
    await process_due_message_deletions(bot)


    # 7. Start Lightweight HTTP Keep-Alive Server
    web_runner = await start_web_server(host="0.0.0.0", port=settings.PORT)

    # 8. Start Bot Polling
    logger.info("Kvartira Bot is now polling for updates...")
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down bot and web server...")
        await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Kvartira Bot stopped.")
