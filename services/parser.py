import re
from typing import Optional, Dict, Any
from aiogram import types
from bot.core.config import settings

class LeadParser:
    def __init__(self):
        # Улучшенные регулярные выражения для поиска данных
        self.phone_pattern = re.compile(r'(?:\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}')
        self.area_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(?:м2|кв\.?\s*м|квадратных\s*метров?)')
        self.name_patterns = [
            r'(?:имя|заказчик|клиент|контакт)(?::|)\s*([^\n]+)',
            r'([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})',
            r'^([^\n]+)'
        ]
        self.category_patterns = {
            "Ремонт квартир под ключ": [
                r'ремонт\s+(?:квартир|помещени[йя])',
                r'отделк[аи]\s+(?:квартир|помещени[йя])',
                r'ремонт\s+под\s+ключ'
            ],
            "Установка окон": [
                r'(?:установк[аи]|замен[аи]|монтаж)\s+окон',
                r'пластиковые\s+окна',
                r'остеклени[ея]'
            ],
            "Кухни": [
                r'кухн[яи]',
                r'кухонн(?:ый|ая|ое)\s+гарнитур',
                r'мебель\s+для\s+кухни'
            ]
        }

    def _find_name(self, text: str) -> Optional[str]:
        """Find name in text using multiple patterns."""
        text_lines = text.split('\n')
        
        # Пробуем найти имя по шаблонам
        for pattern in self.name_patterns:
            for line in text_lines:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Проверяем, что это похоже на имя (начинается с заглавной буквы)
                    if name and name[0].isupper():
                        return name
        return None

    def _find_category(self, text: str) -> Optional[str]:
        """Find category in text using multiple patterns."""
        text = text.lower()
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return None

    def _find_city(self, text: str) -> Optional[str]:
        """Find city in text."""
        text = text.lower()
        # Сначала ищем точные совпадения
        for city in settings.CITIES:
            if city.lower() in text:
                return city
            
        # Затем ищем вариации написания
        city_variations = {
            "Москва": [r'мск', r'москв[аеу]'],
            "Санкт-Петербург": [r'спб', r'питер', r'санкт'],
            "Краснодар": [r'краснодар[ае]', r'кдр']
        }
        
        for city, patterns in city_variations.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return city
        return None

    async def parse_message(self, message: types.Message) -> Optional[Dict[str, Any]]:
        """Parse lead information from message."""
        if not message.text:
            return None

        text = message.text
        
        # Extract phone number
        phone_match = self.phone_pattern.search(text)
        phone = phone_match.group(0) if phone_match else None
        
        # Extract area
        area_match = self.area_pattern.search(text.lower())
        area = float(area_match.group(1)) if area_match else None
        
        # Find category using improved patterns
        category = self._find_category(text)
        
        # Find city using improved patterns
        city = self._find_city(text)
        
        # Find name using improved patterns
        name = self._find_name(text)
        
        # Если не нашли критически важные поля, возвращаем None
        if not (category and city):
            return None
            
        # Формируем описание, удаляя технические детали
        description = text
        if phone:
            description = description.replace(phone, '[номер телефона]')
        
        return {
            "source_chat_id": message.chat.id,
            "source_message_id": message.message_id,
            "name": name,
            "phone": phone,
            "category": category,
            "city": city,
            "description": description,
            "area": area
        }

    def format_lead_message(self, lead_data: Dict[str, Any]) -> str:
        """Format lead data for sending to users."""
        message_parts = []
        
        if lead_data.get("name"):
            message_parts.append(f"👤 Имя: {lead_data['name']}")
        
        if lead_data.get("phone"):
            message_parts.append(f"📱 Телефон: {lead_data['phone']}")
        
        message_parts.extend([
            f"🏢 Город: {lead_data['city']}",
            f"📋 Категория: {lead_data['category']}"
        ])
        
        if lead_data.get("area"):
            message_parts.append(f"📐 Площадь: {lead_data['area']} м²")
        
        message_parts.append("\n📝 Описание:")
        message_parts.append(lead_data["description"])
        
        return "\n".join(message_parts) 