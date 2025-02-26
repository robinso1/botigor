from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_paid = Column(Boolean, default=False)
    categories = Column(JSON, default=list)
    cities = Column(JSON, default=list)
    is_demo = Column(Boolean, default=False)
    last_lead_at = Column(DateTime, nullable=True)
    
    # Relationships
    leads = relationship("LeadDistribution", back_populates="user")

    def __repr__(self):
        return f"<User {self.telegram_id}>" 