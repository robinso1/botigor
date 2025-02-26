from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from yookassa import Configuration, Payment as YooKassaPayment
from yookassa.domain.notification import WebhookNotification
from bot.core.config import settings
from bot.models.payment import Payment
from bot.models.user import User
from bot.models.subscription import Subscription
from bot.services.subscription import SubscriptionService
import json
import uuid
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        # Инициализация YooKassa
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

    async def create_payment(
        self,
        user_id: int,
        plan_name: str,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create payment for subscription."""
        # Получаем информацию о плане
        plan = settings.SUBSCRIPTION_PLANS[plan_name]
        
        # Создаем уникальный идентификатор платежа
        payment_id = str(uuid.uuid4())
        
        # Формируем метаданные
        metadata = {
            "user_id": user_id,
            "plan_name": plan_name
        }
        
        # Создаем платеж в YooKassa
        payment = YooKassaPayment.create({
            "amount": {
                "value": str(plan["price"]),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or settings.YOOKASSA_RETURN_URL
            },
            "capture": True,
            "description": f"Подписка {plan['name']} на 30 дней",
            "metadata": metadata,
            "payment_id": payment_id
        })
        
        # Сохраняем информацию о платеже в базе
        db_payment = Payment(
            user_id=user_id,
            payment_id=payment_id,
            amount=plan["price"],
            status="created",
            description=f"Подписка {plan['name']} на 30 дней",
            metadata=json.dumps(metadata)
        )
        self.session.add(db_payment)
        await self.session.commit()
        
        return {
            "payment_id": payment_id,
            "confirmation_url": payment.confirmation.confirmation_url,
            "status": payment.status
        }

    async def process_webhook(self, data: Dict[str, Any]) -> bool:
        """Process payment webhook from YooKassa."""
        try:
            # Создаем объект уведомления из входящих данных
            notification = WebhookNotification(data)
            payment = notification.object
            
            # Получаем платеж из базы
            query = select(Payment).where(Payment.payment_id == payment.id)
            result = await self.session.execute(query)
            db_payment = result.scalar_one_or_none()
            
            if not db_payment:
                logger.error(f"Payment {payment.id} not found in database")
                return False
            
            # Обновляем статус платежа
            db_payment.status = payment.status
            
            if payment.status == "succeeded":
                db_payment.paid_at = datetime.utcnow()
                
                # Создаем подписку
                metadata = json.loads(db_payment.metadata)
                subscription_service = SubscriptionService(self.session)
                subscription = await subscription_service.create_subscription(
                    user_id=metadata["user_id"],
                    plan_name=metadata["plan_name"],
                    payment_id=payment.id
                )
                
                # Связываем платеж с подпиской
                db_payment.subscription_id = subscription.id
                
            elif payment.status == "canceled":
                db_payment.refunded_at = datetime.utcnow()
            
            await self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            await self.session.rollback()
            return False

    async def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment status from database and YooKassa."""
        # Получаем платеж из базы
        query = select(Payment).where(Payment.payment_id == payment_id)
        result = await self.session.execute(query)
        payment = result.scalar_one_or_none()
        
        if not payment:
            return None
        
        # Получаем актуальный статус из YooKassa
        yoo_payment = YooKassaPayment.find_one(payment_id)
        
        # Обновляем статус в базе, если он изменился
        if yoo_payment.status != payment.status:
            payment.status = yoo_payment.status
            if yoo_payment.status == "succeeded":
                payment.paid_at = datetime.utcnow()
            elif yoo_payment.status == "canceled":
                payment.refunded_at = datetime.utcnow()
            await self.session.commit()
        
        return {
            "payment_id": payment.payment_id,
            "amount": payment.amount,
            "status": payment.status,
            "created_at": payment.created_at,
            "paid_at": payment.paid_at,
            "refunded_at": payment.refunded_at
        }

    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel payment if possible."""
        try:
            # Получаем платеж из базы
            query = select(Payment).where(Payment.payment_id == payment_id)
            result = await self.session.execute(query)
            payment = result.scalar_one_or_none()
            
            if not payment or payment.status not in ["pending", "created"]:
                return False
            
            # Отменяем платеж в YooKassa
            yoo_payment = YooKassaPayment.cancel(payment_id)
            
            # Обновляем статус в базе
            payment.status = "canceled"
            payment.refunded_at = datetime.utcnow()
            await self.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error canceling payment: {str(e)}", exc_info=True)
            await self.session.rollback()
            return False 