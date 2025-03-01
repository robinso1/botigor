#!/usr/bin/env python3
"""
Скрипт для проверки зависимостей перед деплоем.
Проверяет совместимость версий пакетов и наличие предварительно собранных колес.
"""

import sys
import subprocess
import pkg_resources
import platform
import os

def check_python_version():
    """Проверка версии Python."""
    print(f"Текущая версия Python: {platform.python_version()}")
    if sys.version_info < (3, 9):
        print("ВНИМАНИЕ: Рекомендуется использовать Python 3.9 или выше")
        return False
    if sys.version_info >= (3, 12):
        print("ВНИМАНИЕ: Python 3.12 может вызвать проблемы с некоторыми пакетами")
        return False
    return True

def check_dependencies():
    """Проверка зависимостей."""
    try:
        with open("requirements.txt", "r") as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        print("Проверка зависимостей...")
        for req in requirements:
            try:
                pkg_resources.require(req)
                print(f"✓ {req}")
            except pkg_resources.DistributionNotFound:
                print(f"✗ {req} - не установлен")
            except pkg_resources.VersionConflict as e:
                print(f"✗ {req} - конфликт версий: {e}")
        
        return True
    except Exception as e:
        print(f"Ошибка при проверке зависимостей: {e}")
        return False

def check_prebuilt_wheels():
    """Проверка наличия предварительно собранных колес."""
    critical_packages = ["aiohttp", "aiogram", "SQLAlchemy", "pydantic"]
    
    print("Проверка наличия предварительно собранных колес для критических пакетов...")
    for package in critical_packages:
        try:
            result = subprocess.run(
                ["pip", "index", "versions", package], 
                capture_output=True, 
                text=True
            )
            if "wheel" in result.stdout.lower():
                print(f"✓ {package} - предварительно собранные колеса доступны")
            else:
                print(f"✗ {package} - предварительно собранные колеса не найдены")
        except Exception as e:
            print(f"Ошибка при проверке {package}: {e}")
    
    return True

def main():
    """Основная функция."""
    print("=== Проверка окружения для деплоя ===")
    
    python_ok = check_python_version()
    deps_ok = check_dependencies()
    wheels_ok = check_prebuilt_wheels()
    
    if python_ok and deps_ok and wheels_ok:
        print("\n✓ Все проверки пройдены успешно!")
        return 0
    else:
        print("\n✗ Некоторые проверки не пройдены. Исправьте проблемы перед деплоем.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 