from pydantic_settings import BaseSettings
from typing import List, Dict, Optional
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
    YOOKASSA_SHOP_ID: Optional[str] = ""
    YOOKASSA_SECRET_KEY: Optional[str] = ""
    YOOKASSA_RETURN_URL: Optional[str] = "https://t.me/your_bot"  # URL для возврата после оплаты
    
    # Web server settings
    WEB_SERVER_HOST: str = "0.0.0.0"
    WEB_SERVER_PORT: int = 8000
    
    # Redis settings
    REDIS_URL: str = "redis://localhost"
    
    # Webhook settings
    WEBHOOK_HOST: Optional[str] = ""
    WEBHOOK_PATH: str = "/webhook/bot"
    WEBHOOK_URL: Optional[str] = ""
    
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
        "Москва": ["495", "499", "977", "999", "925", "926", "903", "905", "906", "909"],
        "Санкт-Петербург": ["812", "931", "921", "911", "904", "951", "952", "953"],
        "Краснодар": ["861", "918", "988", "928", "929", "960", "961", "962"]
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
            "Новостройка, требуется ремонт под ключ. 2 комнаты, санузел раздельный. Площадь 65 м².",
            "Вторичка, нужен капитальный ремонт. Сталинский дом, высокие потолки. 85 м².",
            "Студия в новостройке, требуется отделка под ключ. Черновая отделка. 42 м².",
            "Трехкомнатная квартира, косметический ремонт. Срочно. Площадь 78 м².",
            "Нужен ремонт в ванной и кухне. Старый фонд, требуется замена труб. 12 м².",
            "Евроремонт в двушке, новостройка, без перепланировки. 58 м².",
            "Капитальный ремонт в сталинке, 3 комнаты, лепнина. 96 м².",
            "Ремонт в новостройке, white box, требуется только чистовая отделка. 44 м².",
            "Ремонт в коммерческом помещении под офис. Площадь 120 м².",
            "Срочный ремонт после затопления. Спальня и коридор. 35 м²."
        ],
        "Установка окон": [
            "Требуется замена 3 окон в квартире. Сталинка, деревянные окна. Высота 2.1м.",
            "Новостройка, установка 5 окон с балконной дверью. Стандартные размеры.",
            "Нужны окна с повышенной шумоизоляцией. 2 окна в спальню. Панорамные.",
            "Замена старых окон на пластиковые. Всего 4 окна. Хрущевка.",
            "Остекление балкона и лоджии. Теплое остекление. 6 метров.",
            "Панорамное остекление в пентхаусе. 4 окна высотой 3 метра.",
            "Замена окон в коттедже, нужны двухкамерные стеклопакеты. 8 окон.",
            "Остекление веранды в загородном доме. Площадь 15 м².",
            "Срочная замена разбитого окна. Первый этаж, решетки.",
            "Установка мансардных окон. 2 окна с электроприводом."
        ],
        "Кухни": [
            "Нужна кухня под заказ. Размеры 3x4, угловая планировка. Со встроенной техникой.",
            "Кухня с островом, современный стиль. Есть проект. Размеры 4x5.",
            "Требуется компактная кухня для студии. Размеры 2x2.2. Минимализм.",
            "Кухня в классическом стиле с патиной. Эскизы есть. П-образная.",
            "Модульная кухня с встроенной техникой. Размеры 3.6x2.8. Лофт.",
            "Кухня в стиле прованс, с буфетом и витринами. 3.2x3.5 метра.",
            "Современная кухня со скрытой техникой. 4x3 метра, белый глянец.",
            "Угловая кухня с барной стойкой. Размеры 2.8x2.4, темное дерево.",
            "Кухня в скандинавском стиле. Светлое дерево, 3x3 метра.",
            "Компактная кухня для квартиры-студии. 2.5 метра, встроенный холодильник."
        ]
    }
    
    # Base directory
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env file

settings = Settings() 