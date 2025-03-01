#!/usr/bin/env python3
"""
Скрипт для проверки наличия файла .env и копирования его из .env.example, если он отсутствует.
"""

import os
import sys
import shutil

def setup_env():
    """Проверка наличия файла .env и копирование его из .env.example, если он отсутствует."""
    env_file = ".env"
    env_example_file = ".env.example"
    
    # Проверка наличия файла .env
    if os.path.exists(env_file):
        print(f"Файл {env_file} уже существует.")
        return True
    
    # Проверка наличия файла .env.example
    if not os.path.exists(env_example_file):
        print(f"Файл {env_example_file} не найден.")
        return False
    
    # Копирование файла .env.example в .env
    try:
        shutil.copy2(env_example_file, env_file)
        print(f"Файл {env_file} создан на основе {env_example_file}.")
        print("Пожалуйста, отредактируйте файл .env и укажите правильные значения переменных окружения.")
        return True
    except Exception as e:
        print(f"Ошибка при копировании файла: {e}")
        return False

def main():
    """Основная функция."""
    print("Настройка переменных окружения...")
    
    if not setup_env():
        print("Не удалось настроить переменные окружения.")
        sys.exit(1)
    
    print("Настройка переменных окружения завершена.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 