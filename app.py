import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiohttp import web
from bot.core.config import settings
from bot.core.database import get_session_maker
from bot.handlers import base, settings as settings_handler, subscription, admin, webhook
from bot.services.scheduler import SchedulerService
from bot.services.cache import CacheService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=settings.BOT_TOKEN)
storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)

# Создание приложения
app = web.Application()

# Health check endpoint
async def health_handler(request):
    return web.Response(text='OK')

async def start_bot():
    try:
        # Регистрация хендлеров
        dp.include_router(base.router)
        dp.include_router(settings_handler.router)
        dp.include_router(subscription.router)
        dp.include_router(admin.router)
        
        # Инициализация базы данных
        session_maker = get_session_maker()
        
        # Инициализация кеша
        cache_service = CacheService()
        
        # Добавляем сервисы в middleware
        dp["session_maker"] = session_maker
        dp["cache"] = cache_service
        
        # Запуск планировщика
        scheduler = SchedulerService(session_maker, bot)
        scheduler.start()
        
        # Запуск бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}", exc_info=True)
        raise

@app.on_startup
async def on_startup(app):
    try:
        # Запускаем бота в фоновом режиме
        asyncio.create_task(start_bot())
        logger.info("Bot started successfully")
    except Exception as e:
        logger.error(f"Error in startup: {str(e)}", exc_info=True)
        raise

@app.on_shutdown
async def on_shutdown(app):
    try:
        # Закрываем соединения
        await bot.session.close()
        await dp.storage.close()
        logger.info("Bot shutdown completed")
    except Exception as e:
        logger.error(f"Error in shutdown: {str(e)}", exc_info=True)

def create_app():
    # Добавляем маршруты
    app.router.add_get('/health', health_handler)
    
    # Добавляем вебхуки если настроены
    if settings.WEBHOOK_URL:
        webhook.setup_webhook_routes(app)
    
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    web.run_app(create_app(), host='0.0.0.0', port=port) 