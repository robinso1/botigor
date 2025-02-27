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

async def on_startup(bot: Bot, app: web.Application) -> None:
    """Действия при запуске бота."""
    try:
        # Устанавливаем вебхук для бота
        if settings.WEBHOOK_URL:
            await bot.set_webhook(
                url=settings.WEBHOOK_URL,
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to {settings.WEBHOOK_URL}")
        
        # Запускаем планировщик
        scheduler = SchedulerService(app["session_maker"], bot)
        scheduler.start()
        app["scheduler"] = scheduler
        logger.info("Scheduler started")
        
        # Уведомляем администраторов о запуске
        for admin_id in settings.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "🚀 Бот запущен и готов к работе!"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in startup: {str(e)}", exc_info=True)
        raise

async def on_shutdown(bot: Bot, app: web.Application) -> None:
    """Действия при остановке бота."""
    try:
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
        logger.error(f"Error in shutdown: {str(e)}", exc_info=True)

async def health_check(request):
    """Health check endpoint for Railway."""
    return web.Response(text="OK", status=200)

async def create_app():
    """Create and configure application."""
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Создаем приложение
    app = web.Application()
    
    # Добавляем эндпоинт для проверки работоспособности
    app.router.add_get('/health', health_check)
    
    # Инициализация базы данных
    session_maker = get_session_maker()
    app["session_maker"] = session_maker
    app["bot"] = bot
    app["dp"] = dp
    
    # Регистрация middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())
    
    # Регистрация хендлеров
    dp.include_router(base.router)
    dp.include_router(settings_handler.router)
    dp.include_router(subscription.router)
    dp.include_router(admin.router)
    
    # Настройка вебхуков
    if settings.WEBHOOK_URL:
        webhook.setup_webhook_routes(app)
        
        # Регистрация хендлеров запуска/остановки
        app.on_startup.append(lambda app: on_startup(bot, app))
        app.on_shutdown.append(lambda app: on_shutdown(bot, app))
    
    return app

async def main():
    """Entry point for running the bot."""
    app = await create_app()
    
    if settings.WEBHOOK_URL:
        # Запуск веб-сервера
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(
            runner,
            settings.WEB_SERVER_HOST,
            settings.WEB_SERVER_PORT
        )
        await site.start()
        logger.info(f"Web server started at {settings.WEB_SERVER_HOST}:{settings.WEB_SERVER_PORT}")
        
        # Запускаем бесконечный цикл
        await asyncio.Event().wait()
    else:
        # Запуск в режиме long polling
        dp = app["dp"]
        bot = app["bot"]
        await on_startup(bot, app)
        await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True) 