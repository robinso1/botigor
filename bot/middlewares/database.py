from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from bot.models.base import get_session_maker
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self):
        self.processed_messages = {}
        self.cleanup_threshold = 1000  # Очищать историю после 1000 сообщений
        self.session_maker = get_session_maker()
        super().__init__()
    
    def _cleanup_old_messages(self):
        """Clean up old messages from the processed list."""
        if len(self.processed_messages) > self.cleanup_threshold:
            current_time = datetime.now()
            self.processed_messages = {
                msg_id: timestamp 
                for msg_id, timestamp in self.processed_messages.items()
                if current_time - timestamp < timedelta(minutes=5)
            }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Check for duplicate messages
        if isinstance(event, Message):
            message_id = f"{event.chat.id}:{event.message_id}"
            current_time = datetime.now()
            
            # Clean up old messages if needed
            self._cleanup_old_messages()
            
            # Check if message was processed recently
            if message_id in self.processed_messages:
                last_processed = self.processed_messages[message_id]
                if current_time - last_processed < timedelta(seconds=30):
                    logger.info(f"Skipping duplicate message {event.message_id} from user {event.from_user.id}")
                    return
            
            # Mark message as processed
            self.processed_messages[message_id] = current_time
            logger.info(f"Processing message {event.message_id} from user {event.from_user.id}")
        
        # Create new session with retry logic
        max_retries = 3
        retry_delay = 1
        last_error = None
        
        for attempt in range(max_retries):
            session = self.session_maker()
            data["session"] = session
            
            try:
                logger.debug(f"Database session created (attempt {attempt + 1})")
                result = await handler(event, data)
                
                if session.is_active:
                    await session.commit()
                    logger.debug("Session committed successfully")
                
                return result
                
            except SQLAlchemyError as e:
                last_error = e
                logger.error(f"Database error (attempt {attempt + 1}/{max_retries}): {e}")
                
                if session.is_active:
                    await session.rollback()
                    logger.debug("Session rolled back due to error")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                raise
                
            except Exception as e:
                logger.error(f"Non-database error in middleware: {e}", exc_info=True)
                if session.is_active:
                    await session.rollback()
                raise
                
            finally:
                if session.is_active:
                    await session.close()
                    logger.debug("Session closed in finally block")
        
        if last_error:
            raise last_error 