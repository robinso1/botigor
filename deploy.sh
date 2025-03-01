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
    echo -e "${RED}Файл .env не найден. Создайте его на основе .env.example.${NC}"
    exit 1
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

# Коммит изменений в Git
echo -e "${YELLOW}Коммит изменений в Git...${NC}"
git add .
git commit -m "Подготовка к деплою: обновлены зависимости и конфигурация" || true

# Деплой на Railway
echo -e "${YELLOW}Деплой на Railway...${NC}"
railway up

echo -e "${GREEN}Деплой успешно завершен!${NC}" 