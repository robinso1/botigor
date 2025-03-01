from flask import Flask
import os
import subprocess
import sys
import time
import signal
import atexit

app = Flask(__name__)
bot_process = None

@app.route('/')
@app.route('/health')
def health():
    return 'OK'

def start_bot():
    """Запуск основного приложения бота в отдельном процессе."""
    global bot_process
    
    # Проверка переменных окружения
    try:
        subprocess.run([sys.executable, "check_env.py"], check=True)
    except subprocess.CalledProcessError:
        print("Ошибка при проверке переменных окружения")
        return
    
    # Применение миграций
    try:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    except subprocess.CalledProcessError:
        print("Ошибка при применении миграций")
        return
    
    # Запуск основного приложения
    cmd = [
        "gunicorn", 
        "app:create_app()", 
        "--bind", 
        "0.0.0.0:8080", 
        "--worker-class", 
        "aiohttp.GunicornWebWorker", 
        "--workers", 
        "1", 
        "--timeout", 
        "120"
    ]
    
    print(f"Запуск бота с командой: {' '.join(cmd)}")
    bot_process = subprocess.Popen(cmd)
    print(f"Бот запущен с PID: {bot_process.pid}")

def cleanup():
    """Очистка ресурсов при завершении."""
    global bot_process
    if bot_process:
        print(f"Завершение процесса бота (PID: {bot_process.pid})")
        bot_process.terminate()
        try:
            bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.kill()

# Регистрация функции очистки
atexit.register(cleanup)

# Обработка сигналов завершения
for sig in [signal.SIGINT, signal.SIGTERM]:
    signal.signal(sig, lambda s, f: cleanup())

if __name__ == '__main__':
    # Запуск бота
    start_bot()
    
    # Запуск Flask для healthcheck
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port) 