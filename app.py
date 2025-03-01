from aiohttp import web
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.base import get_session_maker
from handlers import setup_routers
from services.scheduler import SchedulerService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Обработчик для проверки работоспособности
async def health_handler(request):
    """Обработчик для проверки работоспособности."""
    return web.Response(text="OK")

async def start_bot():
    """Запуск бота."""
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Настройка роутеров
    router = setup_routers()
    dp.include_router(router)
    
    # Настройка вебхуков (если нужно)
    if settings.WEBHOOK_URL:
        logger.info(f"Setting webhook to {settings.WEBHOOK_URL}")
        await bot.set_webhook(
            url=settings.WEBHOOK_URL,
            drop_pending_updates=True
        )
    
    # Возвращаем бота и диспетчера
    return bot, dp

def create_app():
    """Создание приложения."""
    # Создание приложения
    app = web.Application()
    
    # Добавление маршрутов
    app.router.add_get('/health', health_handler)
    
    # Настройка сессии базы данных
    session_maker = get_session_maker()
    app['session_maker'] = session_maker
    
    # Middleware для сессии базы данных
    @web.middleware
    async def db_session_middleware(request, handler):
        async with session_maker() as session:
            request['session'] = session
            response = await handler(request)
            return response
    
    app.middlewares.append(db_session_middleware)
    
    # Настройка запуска и остановки
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app

async def on_startup(app):
    """Действия при запуске приложения."""
    try:
        # Запуск бота
        bot, dp = await start_bot()
        app['bot'] = bot
        app['dp'] = dp
        
        # Настройка вебхуков (если нужно)
        if settings.WEBHOOK_URL:
            # Настройка обработчика вебхуков
            webhook_requests_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
            )
            setup_application(app, webhook_requests_handler, path=settings.WEBHOOK_PATH)
        else:
            # Запуск поллинга в фоновом режиме
            from aiogram import Bot
            import asyncio
            
            async def start_polling():
                await dp.start_polling(bot)
            
            loop = asyncio.get_event_loop()
            loop.create_task(start_polling())
        
        # Запуск планировщика задач
        scheduler = SchedulerService(app['session_maker'], bot)
        scheduler.start()
        app['scheduler'] = scheduler
        
        logger.info("Bot started successfully")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        raise

async def on_shutdown(app):
    """Действия при остановке приложения."""
    try:
        # Остановка планировщика
        if 'scheduler' in app:
            app['scheduler'].stop()
        
        # Закрытие соединений бота
        if 'bot' in app:
            bot = app['bot']
            if settings.WEBHOOK_URL:
                await bot.delete_webhook()
            await bot.session.close()
        
        logger.info("Bot stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping bot: {e}", exc_info=True)

if __name__ == '__main__':
    # Запуск приложения
    app = create_app()
    port = int(os.environ.get('PORT', 8000))
    web.run_app(app, host='0.0.0.0', port=port)