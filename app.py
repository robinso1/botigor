import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from bot.core.config import settings
from bot.core.database import get_session_maker
from bot.handlers import base, settings as settings_handler, subscription, admin, webhook
from bot.services.scheduler import SchedulerService

# Инициализация бота
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
app = web.Application()

# Health check endpoint
async def health_handler(request):
    return web.Response(text='OK')

async def start_bot():
    # Регистрация хендлеров
    dp.include_router(base.router)
    dp.include_router(settings_handler.router)
    dp.include_router(subscription.router)
    dp.include_router(admin.router)
    
    # Инициализация базы данных
    session_maker = get_session_maker()
    
    # Запуск планировщика
    scheduler = SchedulerService(session_maker, bot)
    scheduler.start()
    
    # Запуск бота
    await dp.start_polling(bot)

@app.on_startup
async def on_startup(app):
    # Запускаем бота в фоновом режиме
    asyncio.create_task(start_bot())

def create_app():
    # Добавляем маршруты
    app.router.add_get('/health', health_handler)
    return app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    web.run_app(create_app(), host='0.0.0.0', port=port) 