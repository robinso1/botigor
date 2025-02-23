from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from bot.core.config import settings
import logging
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Global engine instance
_engine = None
_async_session = None

def get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=True,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    return _engine

def get_session_maker():
    """Get or create session maker."""
    global _async_session
    if _async_session is None:
        _async_session = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session

class Base(DeclarativeBase):
    pass

async def init_models():
    """Initialize database models with retry logic."""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
            return
        except SQLAlchemyError as e:
            logger.error(f"Database initialization error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            raise

@asynccontextmanager
async def get_session() -> AsyncSession:
    """Get database session with automatic cleanup."""
    session = None
    try:
        session = get_session_maker()()
        yield session
        if session.is_active:
            await session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {e}")
        if session and session.is_active:
            await session.rollback()
        raise
    finally:
        if session:
            await session.close()

# For middleware compatibility
async_session = get_session_maker() 