#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Скрипт для исправления проблем с деплоем...${NC}"

# Проверка наличия Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${RED}CLI Railway не установлен. Установите его с помощью 'npm i -g @railway/cli'.${NC}"
    exit 1
fi

# Проверка авторизации в Railway
railway whoami
if [ $? -ne 0 ]; then
    echo -e "${RED}Вы не авторизованы в Railway. Выполните 'railway login'.${NC}"
    exit 1
fi

# Меню выбора действия
echo -e "\n${YELLOW}Выберите действие:${NC}"
echo "1. Проверить статус деплоя"
echo "2. Проверить переменные окружения"
echo "3. Установить необходимые переменные окружения"
echo "4. Перезапустить деплой"
echo "5. Переключиться на healthcheck (для отладки)"
echo "6. Переключиться на основное приложение"
echo "7. Выйти"

read -p "Введите номер действия: " choice

case $choice in
    1)
        echo -e "\n${YELLOW}Получение статуса последнего деплоя...${NC}"
        railway status
        ;;
    2)
        echo -e "\n${YELLOW}Проверка переменных окружения...${NC}"
        railway variables list
        ;;
    3)
        echo -e "\n${YELLOW}Установка необходимых переменных окружения...${NC}"
        railway variables set PORT=8000
        railway variables set PYTHON_VERSION=3.9.18
        railway variables set RENDER=1
        echo -e "${GREEN}Базовые переменные установлены.${NC}"
        
        read -p "Введите BOT_TOKEN: " bot_token
        if [ ! -z "$bot_token" ]; then
            railway variables set BOT_TOKEN=$bot_token
            echo -e "${GREEN}BOT_TOKEN установлен.${NC}"
        fi
        
        read -p "Введите DATABASE_URL (оставьте пустым для SQLite): " db_url
        if [ -z "$db_url" ]; then
            railway variables set DATABASE_URL=sqlite+aiosqlite:///bot.db
            echo -e "${GREEN}DATABASE_URL установлен на SQLite.${NC}"
        else
            railway variables set DATABASE_URL=$db_url
            echo -e "${GREEN}DATABASE_URL установлен.${NC}"
        fi
        ;;
    4)
        echo -e "\n${YELLOW}Перезапуск деплоя...${NC}"
        railway up
        ;;
    5)
        echo -e "\n${YELLOW}Переключение на healthcheck...${NC}"
        cat > railway.toml << 'EOL'
[build]
builder = "nixpacks"
buildCommand = "pip install --no-cache-dir --prefer-binary -r requirements.txt"
watchPatterns = ["requirements.txt"]

[deploy]
startCommand = "python healthcheck.py"
healthcheckPath = "/"
healthcheckTimeout = 60
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 5

[env]
PYTHON_VERSION = "3.9.18"
PORT = "8000"
RENDER = "1"

[nixpacks]
python_version = "3.9.18"

[nixpacks.build.env]
NIXPACKS_PYTHON_BUILD_DEPS = "gcc g++ python3-dev libffi-dev"
PIP_EXTRA_INDEX_URL = "https://pypi.org/simple"
PIP_DISABLE_PIP_VERSION_CHECK = "1"
PIP_NO_CACHE_DIR = "1"
EOL
        git add railway.toml
        git commit -m "Переключение на healthcheck для отладки"
        git push origin main
        echo -e "${GREEN}Конфигурация обновлена для запуска healthcheck.${NC}"
        ;;
    6)
        echo -e "\n${YELLOW}Переключение на основное приложение...${NC}"
        cat > railway.toml << 'EOL'
[build]
builder = "nixpacks"
buildCommand = "pip install --no-cache-dir --prefer-binary -r requirements.txt"
watchPatterns = ["requirements.txt"]

[deploy]
startCommand = "python check_env.py && alembic upgrade head && gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT --worker-class aiohttp.GunicornWebWorker --workers 1 --timeout 120"
healthcheckPath = "/"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 5

[env]
PYTHON_VERSION = "3.9.18"
PORT = "8000"
RENDER = "1"

[nixpacks]
python_version = "3.9.18"

[nixpacks.build.env]
NIXPACKS_PYTHON_BUILD_DEPS = "gcc g++ python3-dev libffi-dev"
PIP_EXTRA_INDEX_URL = "https://pypi.org/simple"
PIP_DISABLE_PIP_VERSION_CHECK = "1"
PIP_NO_CACHE_DIR = "1"
EOL
        git add railway.toml
        git commit -m "Переключение на основное приложение"
        git push origin main
        echo -e "${GREEN}Конфигурация обновлена для запуска основного приложения.${NC}"
        ;;
    7)
        echo -e "${GREEN}Выход.${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Неверный выбор.${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}Операция завершена.${NC}" 