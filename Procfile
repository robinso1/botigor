web: python check_env.py && alembic upgrade head && python -m gunicorn app:create_app() --bind 0.0.0.0:$PORT --worker-class aiohttp.GunicornWebWorker --workers 1 --timeout 120 