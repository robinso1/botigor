#!/usr/bin/env python3
"""
Скрипт для проверки наличия необходимых переменных окружения.
Запускается перед стартом приложения.
"""

import os
import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Обязательные переменные окружения
REQUIRED_ENV_VARS = [
    "BOT_TOKEN",
    "DATABASE_URL",
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
    "REDIS_URL",
]

def check_env_vars():
    """Проверка наличия необходимых переменных окружения."""
    missing_vars = []
    
    logger.info("Проверка переменных окружения...")
    
    for var in REQUIRED_ENV_VARS:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            logger.error(f"Отсутствует обязательная переменная окружения: {var}")
        else:
            logger.info(f"Переменная {var} установлена: {value[:5]}...")
    
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        return False
    
    # Проверка опциональных переменных
    for var in OPTIONAL_ENV_VARS:
        value = os.environ.get(var)
        if not value:
            logger.warning(f"Опциональная переменная окружения {var} не установлена.")
        else:
            logger.info(f"Опциональная переменная {var} установлена: {value[:5] if len(value) > 5 else value}...")
    
    # Модифицируем DATABASE_URL для использования asyncpg
    db_url = os.environ.get("DATABASE_URL", "")
    logger.info(f"Текущий DATABASE_URL: {db_url[:20]}...")
    
    if db_url.startswith("postgresql://"):
        new_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        logger.info(f"Изменение DATABASE_URL с {db_url[:20]}... на {new_db_url[:20]}...")
        os.environ["DATABASE_URL"] = new_db_url
    
    return True

def main():
    """Основная функция."""
    logger.info("Запуск проверки переменных окружения...")
    
    if not check_env_vars():
        logger.error("Проверка переменных окружения не пройдена.")
        sys.exit(1)
    
    logger.info("Все обязательные переменные окружения установлены.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 