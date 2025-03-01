#!/bin/bash
# Скрипт для деплоя проекта

set -e

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Скрипт деплоя бота ===${NC}"

# Проверка зависимостей
echo -e "${YELLOW}Проверка зависимостей...${NC}"
python check_dependencies.py
if [ $? -ne 0 ]; then
    echo -e "${RED}Проверка зависимостей не пройдена. Исправьте проблемы перед деплоем.${NC}"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo -e "${YELLOW}Файл .env не найден. Убедитесь, что все переменные окружения настроены в Railway.${NC}"
fi

# Проверка подключения к Railway
echo -e "${YELLOW}Проверка подключения к Railway...${NC}"
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

# Проверка переменных окружения в Railway
echo -e "${YELLOW}Проверка переменных окружения в Railway...${NC}"
REQUIRED_VARS=("BOT_TOKEN" "DATABASE_URL")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if ! railway variables get $var &> /dev/null; then
        MISSING_VARS+=($var)
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo -e "${RED}Отсутствуют обязательные переменные окружения в Railway: ${MISSING_VARS[*]}${NC}"
    echo -e "${YELLOW}Добавьте их с помощью команды 'railway variables set VAR=VALUE'${NC}"
    exit 1
fi

# Коммит изменений в Git
echo -e "${YELLOW}Коммит изменений в Git...${NC}"
git add .
git commit -m "Подготовка к деплою: обновлены зависимости и конфигурация" || true

# Деплой на Railway
echo -e "${YELLOW}Деплой на Railway...${NC}"
railway up

echo -e "${GREEN}Деплой успешно завершен!${NC}" 