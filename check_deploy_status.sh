#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Проверка статуса деплоя в Railway...${NC}"

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

# Получение статуса деплоя
echo -e "${YELLOW}Получение статуса последнего деплоя...${NC}"
railway status

echo -e "\n${YELLOW}Проверка переменных окружения...${NC}"
railway variables list

echo -e "\n${YELLOW}Получение логов...${NC}"
railway logs

echo -e "\n${GREEN}Проверка завершена. Если бот не работает, проверьте логи выше.${NC}"
echo -e "${YELLOW}Если вы видите ошибки, связанные с переменными окружения, убедитесь, что все необходимые переменные настроены в Railway.${NC}"
echo -e "${YELLOW}Необходимые переменные: BOT_TOKEN, DATABASE_URL, PORT=8000, PYTHON_VERSION=3.9.18, RENDER=1${NC}" 