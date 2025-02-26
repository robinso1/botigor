from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    payment_id = Column(String, unique=True, nullable=False)  # ID платежа в платежной системе
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    status = Column(String, nullable=False)  # created, pending, succeeded, canceled, failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)
    metadata = Column(String, nullable=True)  # JSON строка с дополнительными данными
    
    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payment")

    def __repr__(self):
        return f"<Payment {self.payment_id} {self.status}>" 