from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_name = Column(String, nullable=False)  # basic, pro, premium
    price = Column(Integer, nullable=False)
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    payment_id = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription {self.user_id} {self.plan_name}>"

    @property
    def is_valid(self):
        """Check if subscription is valid."""
        return self.is_active and self.expires_at > datetime.utcnow() 