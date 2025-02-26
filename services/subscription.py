from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.subscription import Subscription
from bot.models.user import User
from bot.core.config import settings
from bot.services.cache import CacheService
import logging

logger = logging.getLogger(__name__)

class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = CacheService()
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.plans = {
            "basic": {
                "name": "Basic",
                "price": 990,
                "duration_days": 30,
                "description": "Базовый тариф:\n"
                             "• Доступ к заявкам на 30 дней\n"
                             "• Просмотр контактов клиентов\n"
                             "• До 30 заявок в месяц"
            },
            "pro": {
                "name": "Pro",
                "price": 1990,
                "duration_days": 30,
                "description": "Продвинутый тариф:\n"
                             "• Доступ к заявкам на 30 дней\n"
                             "• Просмотр контактов клиентов\n"
                             "• До 100 заявок в месяц\n"
                             "• Приоритетное получение заявок"
            },
            "premium": {
                "name": "Premium",
                "price": 4990,
                "duration_days": 30,
                "description": "Премиум тариф:\n"
                             "• Доступ к заявкам на 30 дней\n"
                             "• Просмотр контактов клиентов\n"
                             "• Неограниченное количество заявок\n"
                             "• Мгновенное получение заявок\n"
                             "• Персональный менеджер"
            }
        }
    
    async def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for user."""
        cache_key = f"subscription:user:{user_id}"
        
        async def fetch_subscription():
            query = select(Subscription).where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.is_active == True,
                    Subscription.expires_at > datetime.utcnow()
                )
            )
            result = await self.session.execute(query)
            subscription = result.scalar_one_or_none()
            return subscription.__dict__ if subscription else None
        
        subscription_data = await self.cache.get_or_set(
            cache_key,
            fetch_subscription,
            self.cache_ttl
        )
        
        if subscription_data:
            subscription = Subscription()
            for key, value in subscription_data.items():
                setattr(subscription, key, value)
            return subscription
        return None
    
    async def create_subscription(
        self,
        user_id: int,
        plan_name: str,
        payment_id: Optional[str] = None
    ) -> Subscription:
        """Create new subscription for user."""
        try:
            # Деактивируем текущую подписку
            await self.deactivate_user_subscriptions(user_id)
            
            # Получаем информацию о плане
            plan = settings.SUBSCRIPTION_PLANS[plan_name]
            
            # Создаем новую подписку
            subscription = Subscription(
                user_id=user_id,
                plan_name=plan_name,
                price=plan["price"],
                starts_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=plan["duration_days"]),
                is_active=True,
                payment_id=payment_id
            )
            
            self.session.add(subscription)
            await self.session.commit()
            
            # Инвалидируем кэш
            await self.cache.delete(f"subscription:user:{user_id}")
            await self.cache.invalidate_pattern(f"subscription:stats:*")
            
            return subscription
            
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            await self.session.rollback()
            raise
    
    async def deactivate_user_subscriptions(self, user_id: int) -> None:
        """Deactivate all user's subscriptions."""
        try:
            await self.session.execute(
                update(Subscription)
                .where(
                    and_(
                        Subscription.user_id == user_id,
                        Subscription.is_active == True
                    )
                )
                .values(is_active=False)
            )
            await self.session.commit()
            
            # Инвалидируем кэш
            await self.cache.delete(f"subscription:user:{user_id}")
            await self.cache.invalidate_pattern(f"subscription:stats:*")
            
        except Exception as e:
            logger.error(f"Error deactivating subscriptions: {str(e)}")
            await self.session.rollback()
            raise
    
    async def check_subscriptions(self) -> None:
        """Check and deactivate expired subscriptions."""
        try:
            # Находим все истекшие активные подписки
            query = select(Subscription).where(
                and_(
                    Subscription.is_active == True,
                    Subscription.expires_at <= datetime.utcnow()
                )
            )
            result = await self.session.execute(query)
            expired_subscriptions = result.scalars().all()
            
            # Деактивируем истекшие подписки
            for subscription in expired_subscriptions:
                subscription.is_active = False
                # Инвалидируем кэш для пользователя
                await self.cache.delete(f"subscription:user:{subscription.user_id}")
            
            await self.session.commit()
            
            # Инвалидируем общую статистику
            await self.cache.invalidate_pattern(f"subscription:stats:*")
            
        except Exception as e:
            logger.error(f"Error checking subscriptions: {str(e)}")
            await self.session.rollback()
            raise
    
    async def get_subscription_stats(self) -> Dict:
        """Get subscription statistics."""
        cache_key = "subscription:stats:general"
        
        async def fetch_stats():
            try:
                # Общее количество активных подписок
                active_count = await self.session.scalar(
                    select(func.count(Subscription.id)).where(
                        and_(
                            Subscription.is_active == True,
                            Subscription.expires_at > datetime.utcnow()
                        )
                    )
                )
                
                # Статистика по планам
                stats_by_plan = {}
                for plan_name in settings.SUBSCRIPTION_PLANS.keys():
                    count = await self.session.scalar(
                        select(func.count(Subscription.id)).where(
                            and_(
                                Subscription.plan_name == plan_name,
                                Subscription.is_active == True,
                                Subscription.expires_at > datetime.utcnow()
                            )
                        )
                    )
                    stats_by_plan[plan_name] = count
                
                return {
                    "active_subscriptions": active_count,
                    "by_plan": stats_by_plan,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error fetching subscription stats: {str(e)}")
                return None
        
        return await self.cache.get_or_set(cache_key, fetch_stats, self.cache_ttl)
    
    def get_plan_info(self, plan_name: str) -> Dict:
        """Get plan information."""
        return self.plans[plan_name]
    
    def get_all_plans(self) -> List[Dict]:
        """Get all available plans."""
        return [
            {"id": plan_id, **plan_info}
            for plan_id, plan_info in self.plans.items()
        ] 