import random
from typing import List, Dict

DEMO_NAMES = [
    "Александр", "Елена", "Дмитрий", "Ольга", "Сергей",
    "Анна", "Михаил", "Татьяна", "Андрей", "Мария"
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

def generate_phone() -> str:
    """Generate a random phone number."""
    return f"+7{random.randint(9000000000, 9999999999)}"

def mask_phone(phone: str, is_paid: bool) -> str:
    """Mask phone number for unpaid users."""
    if is_paid:
        return phone
    return phone[:5] + "*" * 6

def generate_demo_lead(category: str, city: str) -> Dict:
    """Generate a demo lead with given category and city."""
    return {
        "name": random.choice(DEMO_NAMES),
        "phone": generate_phone(),
        "category": category,
        "city": city,
        "description": random.choice(DEMO_DESCRIPTIONS),
        "area": random.choice(DEMO_AREAS),
        "source_chat_id": 0,
        "source_message_id": 0
    } 