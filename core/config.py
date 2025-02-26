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
    MAX_RECIPIENTS: int = 3  # maximum number of users to receive one lead
    DEMO_LEADS_PER_DAY: int = 5  # number of demo leads per user per day
    
    # Payment settings
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_RETURN_URL: str = "https://t.me/your_bot"  # URL для возврата после оплаты
    
    # Subscription plans
    SUBSCRIPTION_PLANS: Dict[str, Dict] = {
        "basic": {
            "name": "Basic",
            "price": 990,
            "duration_days": 30,
            "leads_limit": 30,
            "delay_hours": 1,
            "description": "Базовый тариф:\n• Доступ к заявкам на 30 дней\n• Просмотр контактов клиентов\n• До 30 заявок в месяц"
        },
        "pro": {
            "name": "Pro",
            "price": 1990,
            "duration_days": 30,
            "leads_limit": 100,
            "delay_hours": 0.5,
            "description": "Продвинутый тариф:\n• Доступ к заявкам на 30 дней\n• Просмотр контактов клиентов\n• До 100 заявок в месяц\n• Приоритетное получение заявок"
        },
        "premium": {
            "name": "Premium",
            "price": 4990,
            "duration_days": 30,
            "leads_limit": float('inf'),
            "delay_hours": 0,
            "description": "Премиум тариф:\n• Доступ к заявкам на 30 дней\n• Просмотр контактов клиентов\n• Неограниченное количество заявок\n• Мгновенное получение заявок\n• Персональный менеджер"
        }
    }
    
    # Lead categories and cities
    CATEGORIES: List[str] = [
        "Ремонт квартир под ключ",
        "Установка окон",
        "Кухни"
    ]
    
    CITIES: List[str] = [
        "Москва",
        "Санкт-Петербург",
        "Краснодар"
    ]
    
    # City phone prefixes for demo leads
    CITY_PREFIXES: Dict[str, List[str]] = {
        "Москва": ["495", "499", "977", "999"],
        "Санкт-Петербург": ["812", "931", "921"],
        "Краснодар": ["861", "918", "988"]
    }
    
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
    
    # Demo mode settings
    DEMO_DESCRIPTIONS: Dict[str, List[str]] = {
        "Ремонт квартир под ключ": [
            "Новостройка, требуется ремонт под ключ. 2 комнаты, санузел раздельный.",
            "Вторичка, нужен капитальный ремонт. Сталинский дом, высокие потолки.",
            "Студия в новостройке, требуется отделка под ключ. Черновая отделка.",
            "Трехкомнатная квартира, косметический ремонт. Срочно.",
            "Нужен ремонт в ванной и кухне. Старый фонд, требуется замена труб."
        ],
        "Установка окон": [
            "Требуется замена 3 окон в квартире. Сталинка, деревянные окна.",
            "Новостройка, установка 5 окон с балконной дверью.",
            "Нужны окна с повышенной шумоизоляцией. 2 окна в спальню.",
            "Замена старых окон на пластиковые. Всего 4 окна.",
            "Остекление балкона и лоджии. Теплое остекление."
        ],
        "Кухни": [
            "Нужна кухня под заказ. Размеры 3x4, угловая планировка.",
            "Кухня с островом, современный стиль. Есть проект.",
            "Требуется компактная кухня для студии. Размеры 2x2.2.",
            "Кухня в классическом стиле с патиной. Эскизы есть.",
            "Модульная кухня с встроенной техникой. Размеры 3.6x2.8."
        ]
    }
    
    # Base directory
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    
    class Config:
        env_file = ".env"

settings = Settings() 