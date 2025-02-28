from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.lead import Lead, LeadDistribution
from bot.models.user import User
from bot.models.subscription import Subscription
from bot.core.config import settings
from bot.services.demo_data import generate_demo_lead, mask_phone, is_working_hours
from bot.services.cache import CacheService
import logging

logger = logging.getLogger(__name__)

class DistributionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = CacheService()
        self.cache_ttl = 300  # 5 minutes cache TTL
        
        # Лимиты заявок для разных тарифов
        self.plan_limits = {
            plan_name: plan_data["leads_limit"]
            for plan_name, plan_data in settings.SUBSCRIPTION_PLANS.items()
        }
        
        # Задержки для разных тарифов
        self.plan_delays = {
            plan_name: plan_data["delay_hours"]
            for plan_name, plan_data in settings.SUBSCRIPTION_PLANS.items()
        }

    async def get_eligible_users(
        self,
        category: str,
        city: str,
        exclude_users: List[int] = None
    ) -> List[User]:
        """Get users eligible for lead distribution."""
        cache_key = f"distribution:eligible_users:{category}:{city}"
        if exclude_users:
            cache_key += f":{','.join(map(str, exclude_users))}"
        
        async def fetch_eligible_users():
            try:
                # Базовый запрос для пользователей
                query = (
                    select(User)
                    .where(
            and_(
                User.is_active == True,
                            User.categories.contains([category]),
                            User.cities.contains([city])
                        )
                    )
                    .join(Subscription, and_(
                        Subscription.user_id == User.id,
                        Subscription.is_active == True,
                        Subscription.expires_at > datetime.utcnow()
                    ))
                )
                
                if exclude_users:
                    query = query.where(User.id.notin_(exclude_users))
                
                result = await self.session.execute(query)
                users = result.scalars().all()
                
                # Фильтруем пользователей по лимитам заявок
                eligible_users = []
                for user in users:
                    if await self.can_receive_lead(user.id):
                        eligible_users.append(user.__dict__)
                
                return eligible_users
                
            except Exception as e:
                logger.error(f"Error fetching eligible users: {str(e)}")
                return []
        
        users_data = await self.cache.get_or_set(
            cache_key,
            fetch_eligible_users,
            self.cache_ttl
        )
        
        if users_data:
            users = []
            for user_data in users_data:
                user = User()
                for key, value in user_data.items():
                    setattr(user, key, value)
                users.append(user)
            return users
        return []

    async def can_receive_lead(self, user_id: int) -> bool:
        """Check if user can receive more leads."""
        cache_key = f"distribution:can_receive:{user_id}"
        
        async def check_lead_limit():
            try:
                # Получаем активную подписку пользователя
                subscription = await self.get_user_subscription(user_id)
                if not subscription:
                    return False
                
                # Получаем лимит для тарифа
                lead_limit = self.plan_limits.get(subscription.plan_name, 0)
                if lead_limit == float('inf'):
                    return True
                
                # Считаем количество полученных заявок в текущем месяце
                month_start = datetime.utcnow().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                
                leads_count = await self.session.scalar(
                    select(func.count(LeadDistribution.id))
                    .where(
                        and_(
                            LeadDistribution.user_id == user_id,
                            LeadDistribution.sent_at >= month_start
                        )
                    )
                )
                
                return leads_count < lead_limit
                
            except Exception as e:
                logger.error(f"Error checking lead limit: {str(e)}")
                return False
        
        return await self.cache.get_or_set(
            cache_key,
            check_lead_limit,
            60  # 1 minute TTL for this check
        )

    async def get_user_groups(
        self,
        users: List[User]
    ) -> Dict[str, List[User]]:
        """Group users by subscription type."""
        groups = {
            "premium": [],
            "pro": [],
            "basic": []
        }
        
        for user in users:
            subscription = await self.get_user_subscription(user.id)
            if subscription:
                if subscription.plan_name in groups:
                    groups[subscription.plan_name].append(user)
        
        return groups

    async def get_user_subscription(self, user_id: int) -> Optional[Subscription]:
        """Get user's active subscription."""
        cache_key = f"distribution:user_subscription:{user_id}"
        
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

    async def create_distribution(
        self,
        lead_id: int,
        user_id: int
    ) -> Optional[LeadDistribution]:
        """Create lead distribution entry."""
        try:
            # Получаем подписку пользователя для определения задержки
            subscription = await self.get_user_subscription(user_id)
            if not subscription:
                return None
            
            # Определяем задержку отправки
            delay_hours = self.plan_delays.get(subscription.plan_name, 1)
            send_at = datetime.utcnow() + timedelta(hours=delay_hours)
            
            # Создаем запись о распределении
            distribution = LeadDistribution(
                lead_id=lead_id,
                user_id=user_id,
                sent_at=send_at
            )
            
            self.session.add(distribution)
            await self.session.commit()
            
            # Инвалидируем кэш
            await self.cache.delete(f"distribution:can_receive:{user_id}")
            await self.cache.invalidate_pattern(f"distribution:eligible_users:*")
            
            return distribution
            
        except Exception as e:
            logger.error(f"Error creating distribution: {str(e)}")
            await self.session.rollback()
            return None

    async def get_distribution_stats(self) -> Dict:
        """Get distribution statistics."""
        cache_key = "distribution:stats:general"
        
        async def fetch_stats():
            try:
                # Статистика за текущий месяц
                month_start = datetime.utcnow().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
                
                # Общее количество распределенных заявок
                total_leads = await self.session.scalar(
                    select(func.count(LeadDistribution.id))
                    .where(LeadDistribution.sent_at >= month_start)
                )
                
                # Статистика по категориям
                leads_by_category = {}
                for category in settings.CATEGORIES:
                    count = await self.session.scalar(
                        select(func.count(LeadDistribution.id))
                        .join(Lead)
                        .where(
                            and_(
                                Lead.category == category,
                                LeadDistribution.sent_at >= month_start
                            )
                        )
                    )
                    leads_by_category[category] = count
                
                # Статистика по городам
                leads_by_city = {}
                for city in settings.CITIES:
                    count = await self.session.scalar(
                        select(func.count(LeadDistribution.id))
                        .join(Lead)
                        .where(
                            and_(
                                Lead.city == city,
                                LeadDistribution.sent_at >= month_start
                            )
                        )
                    )
                    leads_by_city[city] = count
                
                return {
                    "total_leads": total_leads,
                    "by_category": leads_by_category,
                    "by_city": leads_by_city,
                    "period": {
                        "start": month_start.isoformat(),
                        "end": datetime.utcnow().isoformat()
                    }
                }
                
            except Exception as e:
                logger.error(f"Error fetching distribution stats: {str(e)}")
                return None
        
        return await self.cache.get_or_set(cache_key, fetch_stats, self.cache_ttl)

    async def get_next_group_index(self, category: str) -> int:
        """Get index of next group to receive leads."""
        # Get total number of leads for this category today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count(Lead.id)).where(
            and_(
                Lead.category == category,
                Lead.created_at >= today_start
            )
        )
        total_leads = await self.session.scalar(query)
        if total_leads is None:
            total_leads = 0
        return total_leads % 2

    async def distribute_lead(self, lead: Lead, include_demo: bool = False) -> List[LeadDistribution]:
        """Distribute lead to eligible users according to the specified algorithm."""
        # Get eligible users
        users = await self.get_eligible_users(lead.category, lead.city)
        if not users:
            return []

        # Split users into groups
        user_groups = await self.get_user_groups(users)
        if not user_groups:
            return []

        # Determine which group should receive the lead
        group_index = await self.get_next_group_index(lead.category)
        
        # If group_index is 1, we go in reverse order
        if group_index == 1:
            user_groups = list(reversed(user_groups))

        # Get the target group (first group after reordering)
        target_group = user_groups[0] if user_groups else []
        
        # Create distributions with delays
        distributions = []
        for i, user in enumerate(target_group):
            distribution = await self.create_distribution(
                lead_id=lead.id,
                user_id=user.id
            )
            distributions.append(distribution)
        
        return distributions

    async def create_demo_lead(self) -> Optional[Lead]:
        """Create a demo lead for testing."""
        # Проверяем рабочее время
        if not is_working_hours():
            return None
            
        category = random.choice(settings.CATEGORIES)
        city = random.choice(settings.CITIES)
        demo_data = generate_demo_lead(category, city)
        
        lead = Lead(**demo_data)
        self.session.add(lead)
        await self.session.commit()
        return lead

    async def get_pending_distributions(self) -> List[LeadDistribution]:
        """Get distributions that are ready to be sent."""
        query = select(LeadDistribution).where(
            and_(
                LeadDistribution.sent_at <= datetime.utcnow(),
                LeadDistribution.viewed_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def mark_distribution_viewed(self, distribution_id: int) -> Optional[LeadDistribution]:
        """Mark distribution as viewed."""
        query = select(LeadDistribution).where(LeadDistribution.id == distribution_id)
        result = await self.session.execute(query)
        distribution = result.scalar_one_or_none()
        
        if distribution:
            distribution.viewed_at = datetime.utcnow()
            await self.session.commit()
            
        return distribution

    def format_lead_for_user(self, lead: Lead, user: User) -> str:
        """Format lead data for sending to user with phone masking."""
        message_parts = []
        
        if lead.name:
            message_parts.append(f"👤 Имя: {lead.name}")
        
        if lead.phone:
            masked_phone = mask_phone(lead.phone, user.is_paid)
            message_parts.append(f"📱 Телефон: {masked_phone}")
        
        message_parts.extend([
            f"🏢 Город: {lead.city}",
            f"📋 Категория: {lead.category}"
        ])
        
        # Форматируем площадь в зависимости от категории
        if lead.area:
            if lead.category == "Установка окон":
                message_parts.append(f"🪟 Количество окон: {int(lead.area)} шт.")
            else:
            message_parts.append(f"📐 Площадь: {lead.area} м²")
        
        message_parts.append("\n📝 Описание:")
        message_parts.append(lead.description)
        
        if not user.is_paid:
            message_parts.append("\n⚠️ Для просмотра полного номера телефона необходимо оплатить доступ.")
        
        return "\n".join(message_parts) 