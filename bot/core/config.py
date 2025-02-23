from pydantic_settings import BaseSettings
from typing import List, Dict
from pathlib import Path
import os

class Settings(BaseSettings):
    # Bot settings
    BOT_TOKEN: str
    ADMIN_IDS: List[int] = [922721753, 6104831967]
    
    # Database settings
    DATABASE_URL: str = f"sqlite+aiosqlite:///{'/app/data' if os.getenv('RENDER') else '.'}/bot.db"
    
    # Distribution settings
    DISTRIBUTION_INTERVAL: int = 3  # hours
    MAX_RECIPIENTS: int = 5  # maximum number of users to receive one lead
    
    # Lead categories and cities
    CATEGORIES: List[str] = [
        "Ремонт помещений",
        "Установка окон",
        "Кухни"
    ]
    
    CITIES: List[str] = [
        "Москва",
        "Санкт-Петербург",
        "Краснодар"
    ]
    
    # Lead statuses
    LEAD_STATUSES: Dict[str, str] = {
        "active": "Актуальная",
        "inactive_unavailable": "Не актуальна (недоступен)",
        "inactive_refused": "Не актуальна (отказ)",
        "in_progress": "В работе",
        "measurement": "Замер",
        "thinking": "Думает",
        "contract": "Договор"
    }
    
    # Base directory
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    
    class Config:
        env_file = ".env"

settings = Settings() 