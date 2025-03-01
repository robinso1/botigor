#!/usr/bin/env python3
"""
Скрипт для проверки наличия необходимых переменных окружения перед запуском приложения.
"""

import os
import sys
import logging
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Обязательные переменные окружения
REQUIRED_ENV_VARS = [
    "BOT_TOKEN",
    "DATABASE_URL"
]

# Опциональные переменные окружения
OPTIONAL_ENV_VARS = [
    "ADMIN_IDS",
    "YOOKASSA_SHOP_ID",
    "YOOKASSA_SECRET_KEY",
    "YOOKASSA_RETURN_URL",
    "WEBHOOK_HOST",
    "WEBHOOK_PATH",
    "WEBHOOK_URL",
    "WEB_SERVER_HOST",
    "WEB_SERVER_PORT",
    "REDIS_URL"
]

def check_env_vars():
    """Проверка наличия необходимых переменных окружения."""
    logger.info("Запуск проверки переменных окружения...")
    
    logger.info("Проверка переменных окружения...")
    missing_vars = []
    
    # Проверка обязательных переменных
    for var in REQUIRED_ENV_VARS:
        if var in os.environ:
            # Маскируем значение для безопасности в логах
            value = os.environ[var]
            masked_value = value[:5] + "..." if len(value) > 8 else "***"
            logger.info(f"Переменная {var} установлена: {masked_value}")
        else:
            logger.error(f"Обязательная переменная окружения {var} не установлена.")
            missing_vars.append(var)
    
    # Проверка опциональных переменных
    for var in OPTIONAL_ENV_VARS:
        if var in os.environ:
            # Маскируем значение для безопасности в логах
            value = os.environ[var]
            masked_value = value[:5] + "..." if len(value) > 8 else "***"
            logger.info(f"Опциональная переменная {var} установлена: {masked_value}")
        else:
            logger.warning(f"Опциональная переменная окружения {var} не установлена.")
    
    # Проверка и корректировка DATABASE_URL для асинхронной работы
    if "DATABASE_URL" in os.environ:
        db_url = os.environ["DATABASE_URL"]
        logger.info(f"Текущий DATABASE_URL: {db_url[:10]}...")
        
        # Проверяем, содержит ли URL уже asyncpg
        if "postgresql+asyncpg://" not in db_url:
            # Заменяем postgresql:// на postgresql+asyncpg://
            new_db_url = re.sub(r'^postgresql://', 'postgresql+asyncpg://', db_url)
            os.environ["DATABASE_URL"] = new_db_url
            logger.info(f"Изменение DATABASE_URL с {db_url[:10]}... на {new_db_url[:20]}...")
    
    # Проверка наличия отсутствующих обязательных переменных
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        return False
    
    logger.info("Все обязательные переменные окружения установлены.")
    return True

def main():
    """Основная функция."""
    if not check_env_vars():
        logger.error("Проверка переменных окружения не пройдена.")
        sys.exit(1)
    
    logger.info("Проверка переменных окружения пройдена успешно.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 