import random
from typing import List, Dict
from datetime import datetime, time
from bot.core.config import settings

DEMO_NAMES = [
    "Александр", "Елена", "Дмитрий", "Ольга", "Сергей",
    "Анна", "Михаил", "Татьяна", "Андрей", "Мария",
    "Игорь", "Наталья", "Павел", "Екатерина", "Владимир",
    "Светлана", "Артём", "Юлия", "Денис", "Ирина"
]

DEMO_SURNAMES = [
    "Иванов", "Петров", "Смирнов", "Кузнецов", "Попов",
    "Васильев", "Соколов", "Михайлов", "Новиков", "Федоров",
    "Морозов", "Волков", "Алексеев", "Лебедев", "Семенов",
    "Егоров", "Павлов", "Козлов", "Степанов", "Николаев"
]

DEMO_DESCRIPTIONS = [
    "Нужен ремонт в двухкомнатной квартире. Новостройка.",
    "Требуется установка пластиковых окон в частном доме.",
    "Хочу заказать кухню под ключ. Есть свой проект.",
    "Необходим косметический ремонт в ванной комнате.",
    "Интересует установка окон с ламинацией.",
    "Нужна кухня с островом, помещение 15 кв.м.",
    "Требуется капитальный ремонт в студии.",
    "Рассматриваю варианты кухонных гарнитуров.",
    "Нужно установить 5 окон в загородном доме.",
    "Планирую ремонт в новой квартире под ключ."
]

DEMO_AREAS = [
    30, 45, 60, 75, 90, 120, 150, 180, 200, 250
]

def get_area_by_category(category: str) -> float:
    """Get realistic area based on category."""
    if category == "Ремонт квартир под ключ":
        return round(random.uniform(30, 150), 1)
    elif category == "Кухни":
        return round(random.uniform(6, 20), 1)
    else:  # Окна
        return round(random.uniform(1, 6), 0)  # Количество окон

def generate_phone(city: str) -> str:
    """Generate a random phone number with city prefix."""
    prefixes = settings.CITY_PREFIXES[city]
    prefix = random.choice(prefixes)
    
    if prefix in ["495", "499", "812", "861"]:  # Городские номера
        number = random.randint(1000000, 9999999)
        return f"+7 ({prefix}) {number}"
    else:  # Мобильные номера
        number = random.randint(1000000, 9999999)
        return f"+7 {prefix} {number}"

def mask_phone(phone: str, is_paid: bool) -> str:
    """Mask phone number for unpaid users."""
    if is_paid:
        return phone
    
    # Сохраняем формат номера, но маскируем цифры
    parts = phone.split()
    if len(parts) == 3:  # Городской номер: +7 (495) 1234567
        return f"{parts[0]} {parts[1]} {'*' * len(parts[2])}"
    else:  # Мобильный номер: +7 999 1234567
        return f"{parts[0]} {parts[1]} {'*' * len(parts[2])}"

def is_working_hours() -> bool:
    """Check if current time is within working hours (9:00 - 21:00)."""
    now = datetime.now().time()
    return time(9, 0) <= now <= time(21, 0)

def generate_demo_lead(category: str, city: str) -> Dict:
    """Generate a demo lead with given category and city."""
    name = f"{random.choice(DEMO_NAMES)} {random.choice(DEMO_SURNAMES)}"
    area = get_area_by_category(category)
    description = random.choice(settings.DEMO_DESCRIPTIONS[category])
    
    # Добавляем площадь в описание, если это не окна
    if category != "Установка окон":
        description += f"\nПлощадь: {area} м²"
    else:
        description += f"\nКоличество окон: {int(area)} шт."
    
    return {
        "name": name,
        "phone": generate_phone(city),
        "category": category,
        "city": city,
        "description": description,
        "area": area,
        "source_chat_id": 0,
        "source_message_id": 0,
        "created_at": datetime.now()
    } 