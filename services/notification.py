from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.user import User
from bot.models.subscription import Subscription
from bot.models.lead_distribution import LeadDistribution
from bot.core.config import settings
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, session: AsyncSession, bot):
        self.session = session
        self.bot = bot

    async def notify_subscription_expiring(self, days_before: int = 3) -> None:
        """Notify users about expiring subscriptions."""
        expiration_date = datetime.utcnow() + timedelta(days=days_before)
        
        # Находим подписки, которые истекают через days_before дней
        query = select(Subscription).where(
            and_(
                Subscription.is_active == True,
                Subscription.expires_at <= expiration_date,
                Subscription.expires_at > datetime.utcnow()
            )
        ).join(User)
        
        result = await self.session.execute(query)
        subscriptions = result.scalars().all()
        
        for subscription in subscriptions:
            try:
                # Формируем текст уведомления
                message = (
                    f"⚠️ Внимание! Ваша подписка {subscription.plan_name} "
                    f"истекает {subscription.expires_at.strftime('%d.%m.%Y')}.\n\n"
                    "Для продления подписки используйте команду 💳 Подписка"
                )
                
                # Отправляем уведомление
                await self.bot.send_message(
                    subscription.user.telegram_id,
                    message
                )
                logger.info(f"Sent expiration notification to user {subscription.user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Error sending notification to user {subscription.user.telegram_id}: {str(e)}")

    async def notify_leads_limit(self, threshold: float = 0.8) -> None:
        """Notify users when they are close to their leads limit."""
        # Получаем начало текущего месяца
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Находим активные подписки
        query = select(Subscription).where(
            and_(
                Subscription.is_active == True,
                Subscription.expires_at > datetime.utcnow()
            )
        ).join(User)
        
        result = await self.session.execute(query)
        subscriptions = result.scalars().all()
        
        for subscription in subscriptions:
            try:
                # Получаем лимит для текущего тарифа
                plan = settings.SUBSCRIPTION_PLANS[subscription.plan_name]
                leads_limit = plan["leads_limit"]
                
                if leads_limit == float('inf'):
                    continue
                
                # Получаем количество полученных заявок
                leads_count = await self.session.scalar(
                    select(func.count(LeadDistribution.id)).where(
                        and_(
                            LeadDistribution.user_id == subscription.user_id,
                            LeadDistribution.sent_at >= month_start
                        )
                    )
                )
                
                # Проверяем, достигнут ли порог
                if leads_count >= (leads_limit * threshold):
                    remaining = leads_limit - leads_count
                    message = (
                        f"⚠️ Внимание! Вы приближаетесь к лимиту заявок.\n\n"
                        f"Использовано: {leads_count} из {leads_limit}\n"
                        f"Осталось: {remaining} заявок\n\n"
                        "Для увеличения лимита рассмотрите возможность перехода "
                        "на более высокий тариф."
                    )
                    
                    await self.bot.send_message(
                        subscription.user.telegram_id,
                        message
                    )
                    logger.info(f"Sent leads limit notification to user {subscription.user.telegram_id}")
                    
            except Exception as e:
                logger.error(f"Error checking leads limit for user {subscription.user.telegram_id}: {str(e)}")

    async def notify_new_features(self, message: str, admin_only: bool = False) -> None:
        """Send notification about new features to users."""
        try:
            # Получаем пользователей для рассылки
            query = select(User).where(User.is_active == True)
            if admin_only:
                query = query.where(User.telegram_id.in_(settings.ADMIN_IDS))
            
            result = await self.session.execute(query)
            users = result.scalars().all()
            
            for user in users:
                try:
                    await self.bot.send_message(
                        user.telegram_id,
                        message
                    )
                    logger.info(f"Sent feature notification to user {user.telegram_id}")
                    
                except Exception as e:
                    logger.error(f"Error sending feature notification to user {user.telegram_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error sending feature notifications: {str(e)}")

    async def notify_payment_status(self, user_id: int, payment_id: str, status: str) -> None:
        """Send notification about payment status."""
        try:
            # Получаем пользователя
            query = select(User).where(User.id == user_id)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {user_id} not found for payment notification")
                return
            
            # Формируем сообщение в зависимости от статуса
            if status == "succeeded":
                message = (
                    "✅ Оплата прошла успешно!\n\n"
                    "Ваша подписка активирована. Теперь вы можете "
                    "получать заявки согласно выбранному тарифу."
                )
            elif status == "canceled":
                message = (
                    "❌ Платеж отменен.\n\n"
                    "Если вы хотите попробовать снова, "
                    "воспользуйтесь командой 💳 Подписка"
                )
            elif status == "pending":
                message = (
                    "⏳ Платеж обрабатывается.\n\n"
                    "Пожалуйста, подождите. Мы уведомим вас, "
                    "когда платеж будет обработан."
                )
            else:
                message = (
                    "❌ Возникла ошибка при обработке платежа.\n\n"
                    "Пожалуйста, попробуйте позже или обратитесь "
                    "к администратору."
                )
            
            await self.bot.send_message(
                user.telegram_id,
                message
            )
            logger.info(f"Sent payment notification to user {user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error sending payment notification: {str(e)}")

    async def notify_admins(self, message: str) -> None:
        """Send notification to admin users."""
        for admin_id in settings.ADMIN_IDS:
            try:
                await self.bot.send_message(
                    admin_id,
                    message
                )
                logger.info(f"Sent admin notification to {admin_id}")
                
            except Exception as e:
                logger.error(f"Error sending admin notification to {admin_id}: {str(e)}")

    async def schedule_notifications(self) -> None:
        """Schedule and send all notifications."""
        try:
            # Проверяем истекающие подписки
            await self.notify_subscription_expiring()
            
            # Проверяем лимиты заявок
            await self.notify_leads_limit()
            
            logger.info("Scheduled notifications completed")
            
        except Exception as e:
            logger.error(f"Error in scheduled notifications: {str(e)}")
            # Уведомляем администраторов об ошибке
            await self.notify_admins(
                f"❌ Ошибка при отправке уведомлений:\n{str(e)}"
            ) 