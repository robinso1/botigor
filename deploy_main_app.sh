#!/bin/bash

# Обновляем railway.toml для запуска основного приложения
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

# Коммитим и пушим изменения
git add railway.toml
git commit -m "Переключение на основное приложение после успешного деплоя healthcheck"
git push origin main

echo "Конфигурация обновлена для запуска основного приложения" 