import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from bot.core.config import settings
from bot.core.database import get_session_maker
from bot.handlers import base, settings as settings_handler, subscription, admin, webhook
from bot.services.scheduler import SchedulerService
from bot.middlewares.database import DatabaseMiddleware
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint for Railway."""
    try:
        # Проверяем подключение к боту
        bot = request.app["bot"]
        me = await bot.get_me()
        return web.Response(
            text=f"Bot {me.username} is running",
            status=200
        )
    except Exception as e:
        logger.error(f"Healthcheck failed: {str(e)}")
        return web.Response(
            text="Bot is not responding",
            status=500
        )

async def on_startup(app):
    """Startup handler."""
    try:
        bot = app["bot"]
        # Устанавливаем вебхук
        if settings.WEBHOOK_URL:
            await bot.set_webhook(settings.WEBHOOK_URL)
            logger.info(f"Webhook set to {settings.WEBHOOK_URL}")
        
        # Запускаем планировщик
        scheduler = SchedulerService(app["session_maker"], bot)
        scheduler.start()
        app["scheduler"] = scheduler
        logger.info("Scheduler started")
        
        # Уведомляем администраторов
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🚀 Бот запущен и готов к работе!"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

async def on_shutdown(app):
    """Shutdown handler."""
    try:
        bot = app["bot"]
        # Останавливаем планировщик
        if "scheduler" in app:
            app["scheduler"].stop()
            logger.info("Scheduler stopped")
        
        # Отключаем вебхук
        await bot.delete_webhook()
        logger.info("Webhook removed")
        
        # Закрываем сессии с базой данных
        await app["session_maker"]().close()
        logger.info("Database sessions closed")
        
        # Уведомляем администраторов
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🔄 Бот остановлен для обслуживания."
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Shutdown error: {str(e)}")

async def create_app():
    """Create and configure aiohttp application."""
    # Создаем приложение
    app = web.Application()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Сохраняем их в приложении
    app["bot"] = bot
    app["dp"] = dp
    
    # Инициализация базы данных
    session_maker = get_session_maker()
    app["session_maker"] = session_maker
    
    # Регистрация middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Регистрация хендлеров
    dp.include_router(base.router)
    dp.include_router(settings_handler.router)
    dp.include_router(subscription.router)
    dp.include_router(admin.router)
    
    # Настройка маршрутов
    app.router.add_get('/health', health_check)
    if settings.WEBHOOK_URL:
        webhook.setup_webhook_routes(app)
    
    # Регистрация хендлеров запуска/остановки
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app

def create_app_sync():
    """Synchronous wrapper for create_app."""
    return asyncio.get_event_loop().run_until_complete(create_app())

if __name__ == "__main__":
    app = create_app_sync()
    web.run_app(
        app,
        host=settings.WEB_SERVER_HOST,
        port=settings.WEB_SERVER_PORT
    ) 