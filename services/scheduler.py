from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.services.notification import NotificationService
from bot.services.subscription import SubscriptionService
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, session_maker, bot):
        self.session_maker = session_maker
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def check_subscriptions(self) -> None:
        """Check and update expired subscriptions."""
        try:
            async with self.session_maker() as session:
                subscription_service = SubscriptionService(session)
                await subscription_service.check_subscriptions()
                logger.info("Subscription check completed")
                
        except Exception as e:
            logger.error(f"Error checking subscriptions: {str(e)}", exc_info=True)

    async def send_notifications(self) -> None:
        """Send scheduled notifications."""
        try:
            async with self.session_maker() as session:
                notification_service = NotificationService(session, self.bot)
                await notification_service.schedule_notifications()
                logger.info("Notifications sent")
                
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}", exc_info=True)

    def start(self) -> None:
        """Start scheduler."""
        try:
            # Проверка подписок каждый час
            self.scheduler.add_job(
                self.check_subscriptions,
                CronTrigger(hour='*'),
                name='check_subscriptions',
                misfire_grace_time=None
            )
            
            # Отправка уведомлений каждый день в 10:00
            self.scheduler.add_job(
                self.send_notifications,
                CronTrigger(hour=10, minute=0),
                name='send_notifications',
                misfire_grace_time=None
            )
            
            self.scheduler.start()
            logger.info("Scheduler started")
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}", exc_info=True)

    def stop(self) -> None:
        """Stop scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}", exc_info=True) 