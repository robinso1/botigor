import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError
from core.config import settings
from handlers import base, settings as settings_handlers, admin
from models.base import init_models
from middlewares.database import DatabaseMiddleware

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

async def start_bot():
    """Start bot with error handling and automatic restart."""
    while True:
        try:
            # Initialize bot and dispatcher
            bot = Bot(token=settings.BOT_TOKEN)
            dp = Dispatcher(storage=MemoryStorage())
            
            # Initialize database
            await init_models()
            
            # Add middleware
            dp.message.middleware(DatabaseMiddleware())
            dp.callback_query.middleware(DatabaseMiddleware())
            
            # Register handlers (create new router instances)
            dp.include_router(admin.router)
            dp.include_router(settings_handlers.router)
            dp.include_router(base.router)
            
            logger.info("Starting bot...")
            
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

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        raise 