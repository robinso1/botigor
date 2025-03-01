FROM python:3.9.18-slim
WORKDIR /app
# Установка зависимостей для сборки
RUN apt-get update && apt-get install -y gcc g++ python3-dev libffi-dev curl && apt-get clean && rm -rf /var/lib/apt/lists/*
# Копирование файлов проекта
COPY requirements.txt .
COPY alembic.ini .
COPY check_env.py .
# Установка зависимостей
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt
# Копирование остальных файлов
COPY . .
# Делаем скрипт проверки переменных окружения исполняемым
RUN chmod +x check_env.py
# Применение миграций и запуск приложения
CMD python check_env.py && alembic upgrade head && gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --worker-class aiohttp.GunicornWebWorker --workers 1 --timeout 120
