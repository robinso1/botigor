FROM python:3.9-slim

# Установка зависимостей для PostgreSQL и других библиотек
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для данных
RUN mkdir -p /app/data && chmod 777 /app/data

# Запуск приложения
CMD python check_env.py && \
    alembic upgrade head && \
    python -m gunicorn app:create_app() \
    --bind 0.0.0.0:$PORT \
    --worker-class aiohttp.GunicornWebWorker \
    --workers 1 \
    --timeout 120 