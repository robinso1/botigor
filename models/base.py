from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
import os
import logging
from typing import AsyncGenerator

from bot.core.config import settings

logger = logging.getLogger(__name__)

# Глобальные переменные для хранения движка и фабрики сессий
_engine = None
_session_maker = None

def get_engine():
    """
    Создает и возвращает асинхронный движок SQLAlchemy.
    """
    global _engine
    if _engine is None:
        # Получаем URL базы данных из переменных окружения или настроек
        database_url = os.environ.get("DATABASE_URL", settings.DATABASE_URL)
        
        # Проверяем, содержит ли URL уже asyncpg
        if "postgresql://" in database_url and "postgresql+asyncpg://" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            logger.info(f"URL базы данных изменен на асинхронный: {database_url[:20]}...")
        
        logger.info(f"Создание движка базы данных с URL: {database_url[:20]}...")
        _engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
            pool_pre_ping=True
        )
    return _engine

def get_session_maker():
    """
    Создает и возвращает фабрику асинхронных сессий SQLAlchemy.
    """
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession
        )
    return _session_maker

class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass

async def init_models():
    """
    Инициализирует модели, создавая все таблицы в базе данных.
    """
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            # Создаем все таблицы
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Модели успешно инициализированы")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации моделей: {str(e)}")
        return False

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Контекстный менеджер для получения сессии базы данных.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

# Создаем сессию при импорте модуля
async_session = get_session_maker() 