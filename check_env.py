#!/usr/bin/env python3
"""
Скрипт для проверки наличия необходимых переменных окружения.
Запускается перед стартом приложения.
"""

import os
import sys

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
    
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    # Проверка опциональных переменных
    for var in OPTIONAL_ENV_VARS:
        if not os.environ.get(var):
            print(f"WARNING: Optional environment variable {var} is not set.")
    
    # Модифицируем DATABASE_URL для использования asyncpg
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgresql://"):
        new_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        print(f"Changing DATABASE_URL from {db_url} to {new_db_url}")
        os.environ["DATABASE_URL"] = new_db_url
    
    return True

def main():
    """Основная функция."""
    print("Checking environment variables...")
    
    if not check_env_vars():
        sys.exit(1)
    
    print("All required environment variables are set.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 