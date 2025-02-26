from sqlalchemy import Column, Integer, String, JSON
from .base import Base

class BotSettings(Base):
    __tablename__ = "bot_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(String, nullable=True)

    def __repr__(self):
        return f"<BotSettings {self.key}={self.value}>" 