import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError
from bot.core.config import settings
from bot.handlers import base, settings as settings_handlers, admin
from bot.models.base import init_models
from bot.middlewares.database import DatabaseMiddleware
from datetime import datetime, timedelta
from aiohttp import web
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def handle_polling_error(event: TelegramAPIError):
    """Handle polling errors."""
    logger.error(f"Polling error occurred: {event}", exc_info=True)
    # Notify admins about the error
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        for admin_id in settings.ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"❌ Ошибка в работе бота:\n{str(event)}\n\nБот будет автоматически перезапущен."
            )
    except Exception as e:
        logger.error(f"Failed to notify admins about error: {e}")
    finally:
        await bot.session.close()

async def health_check(request):
    """Handle health check requests."""
    return web.Response(text="OK", status=200)

async def start_web_server():
    """Start web server for health checks."""
    app = web.Application()
    app.router.add_get("/", health_check)
    
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server started on port {port}")

async def start_bot():
    """Start bot with error handling and automatic restart."""
    while True:
        try:
            # Initialize bot and dispatcher
            bot = Bot(token=settings.BOT_TOKEN)
            storage = MemoryStorage()
            dp = Dispatcher(storage=storage)
            
            # Add middleware
            dp.message.middleware(DatabaseMiddleware())
            dp.callback_query.middleware(DatabaseMiddleware())
            
            # Register handlers
            dp.include_router(admin.router)
            dp.include_router(settings_handlers.router)
            dp.include_router(base.router)
            
            logger.info("Starting bot initialization...")
            
            # Initialize database
            await init_models()
            
            # Start web server if running on Render
            if os.getenv("RENDER"):
                await start_web_server()
            
            logger.info("Starting polling...")
            
            # Start polling with automatic restart on errors
            await dp.start_polling(
                bot,
                allowed_updates=[
                    "message",
                    "callback_query",
                    "chat_member",
                    "my_chat_member"
                ],
                error_handler=handle_polling_error
            )
            
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}", exc_info=True)
            try:
                await bot.session.close()
            except Exception:
                pass
            
            # Wait before restart
            await asyncio.sleep(5)
            logger.info("Restarting bot...")
            continue

async def main():
    """Main function with error handling."""
    try:
        await start_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        raise 