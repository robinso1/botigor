from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
from bot.core.config import settings

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    source_chat_id = Column(Integer, nullable=False)
    source_message_id = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    category = Column(String, nullable=False)
    city = Column(String, nullable=False)
    description = Column(String, nullable=True)
    area = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(SQLEnum(*settings.LEAD_STATUSES.keys(), name="lead_status"), default="active")
    
    # Relationships
    distributions = relationship("LeadDistribution", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead {self.id}>"

class LeadDistribution(Base):
    __tablename__ = "lead_distributions"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    viewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    lead = relationship("Lead", back_populates="distributions")
    user = relationship("User", back_populates="leads")

    def __repr__(self):
        return f"<LeadDistribution {self.lead_id} -> {self.user_id}>" 