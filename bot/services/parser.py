import re
from typing import Optional, Dict, Any
from aiogram import types
from bot.core.config import settings

class LeadParser:
    def __init__(self):
        self.phone_pattern = re.compile(r'(?:\+7|8)?[\s\-]?\(?[489][0-9]{2}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}')
        self.area_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(?:м2|кв\.?\s*м)')

    async def parse_message(self, message: types.Message) -> Optional[Dict[str, Any]]:
        """Parse lead information from message."""
        if not message.text:
            return None

        text = message.text.lower()
        
        # Extract phone number
        phone_match = self.phone_pattern.search(message.text)
        phone = phone_match.group(0) if phone_match else None
        
        # Extract area
        area_match = self.area_pattern.search(text)
        area = float(area_match.group(1)) if area_match else None
        
        # Try to determine category
        category = None
        for cat in settings.CATEGORIES:
            if cat.lower() in text:
                category = cat
                break
        
        # Try to determine city
        city = None
        for c in settings.CITIES:
            if c.lower() in text:
                city = c
                break
        
        # Extract name (first line or first word after "имя:" or similar)
        name_match = re.search(r'(?:имя|заказчик|клиент):\s*([^\n]+)', text, re.IGNORECASE)
        name = name_match.group(1) if name_match else None
        
        if not name and '\n' in message.text:
            name = message.text.split('\n')[0].strip()
        
        # If we couldn't determine critical fields, return None
        if not (category and city):
            return None
            
        return {
            "source_chat_id": message.chat.id,
            "source_message_id": message.message_id,
            "name": name,
            "phone": phone,
            "category": category,
            "city": city,
            "description": message.text,
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