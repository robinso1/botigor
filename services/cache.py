from typing import Optional, Any, Union
import json
import aioredis
from datetime import datetime, timedelta
from bot.core.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL)
        self.default_ttl = 3600  # 1 hour default TTL
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            json_value = json.dumps(value)
            await self.redis.set(
                key,
                json_value,
                ex=ttl or self.default_ttl
            )
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False
    
    async def clear_all(self) -> bool:
        """Clear all cache."""
        try:
            await self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        func: callable,
        ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache or set it if not exists."""
        try:
            value = await self.get(key)
            if value is not None:
                return value
            
            value = await func()
            await self.set(key, value, ttl)
            return value
        except Exception as e:
            logger.error(f"Error in get_or_set: {str(e)}")
            return None
    
    async def invalidate_pattern(self, pattern: str) -> bool:
        """Delete all keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Error invalidating pattern: {str(e)}")
            return False 