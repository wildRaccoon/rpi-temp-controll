"""
Швидкий тест програми в тестовому режимі.
Запускає програму на 5 хвилин та перевіряє основні функції.
"""

import sys
import time
import requests
import subprocess
import signal
from datetime import datetime

BASE_URL = "http://localhost:8080"
TEST_DURATION = 300  # 5 хвилин


def test_api_endpoints():
    """Перевірити доступність API ендпоінтів."""
    print("🔍 Перевірка API ендпоінтів...")
    
    endpoints = [
        "/api/status",
        "/api/sensors",
        "/api/system",
        "/api/outlet"
    ]
    
    all_ok = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {endpoint} - OK")
            else:
                print(f"  ❌ {endpoint} - Status: {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"  ❌ {endpoint} - Помилка: {e}")
            all_ok = False
    
    return all_ok


def test_sensors():
    """Перевірити чи датчики повертають дані."""
    print("\n🌡️  Перевірка датчиків...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/sensors", timeout=5)
        if response.status_code == 200:
            data = response.json()
            sensors = data.get('sensors', [])
            
            if len(sensors) > 0:
                print(f"  ✅ Знайдено {len(sensors)} датчик(ів)")
                for sensor in sensors:
                    temp = sensor.get('temperature')
                    status = sensor.get('status')
                    name = sensor.get('name', 'Unknown')
                    if temp is not None:
                        print(f"    - {name}: {temp:.2f}°C ({status})")
                    else:
                        print(f"    - {name}: немає даних ({status})")
                return True
            else:
                print("  ❌ Датчики не знайдено")
                return False
        else:
            print(f"  ❌ Помилка отримання даних: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Помилка: {e}")
        return False


def test_system_state():
    """Перевірити стан системи."""
    print("\n⚙️  Перевірка стану системи...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/system", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Стан системи: {data.get('state')}")
            print(f"    - Котел: {data.get('boiler_temp', 'N/A')}°C")
            print(f"    - Термоакумулятор (низ): {data.get('accumulator_bottom_temp', 'N/A')}°C")
            print(f"    - Термоакумулятор (верх): {data.get('accumulator_top_temp', 'N/A')}°C")
            print(f"    - Димар: {data.get('chimney_temp', 'N/A')}°C")
            print(f"    - Розетка: {data.get('outlet_status')}")
            return True
        else:
            print(f"  ❌ Помилка: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Помилка: {e}")
        return False


def test_web_pages():
    """Перевірити доступність веб-сторінок."""
    print("\n🌐 Перевірка веб-сторінок...")
    
    pages = [
        "/",
        "/status.html",
        "/charts.html"
    ]
    
    all_ok = True
    for page in pages:
        try:
            response = requests.get(f"{BASE_URL}{page}", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {page} - OK")
            else:
                print(f"  ❌ {page} - Status: {response.status_code}")
                all_ok = False
        except Exception as e:
            print(f"  ❌ {page} - Помилка: {e}")
            all_ok = False
    
    return all_ok


def main():
    """Головна функція тесту."""
    print("=" * 60)
    print("🧪 Швидкий тест системи контролю температури")
    print("=" * 60)
    print(f"⏱️  Тривалість тесту: {TEST_DURATION // 60} хвилин")
    print(f"🌐 API URL: {BASE_URL}")
    print()
    
    # Перевірити, чи запущена програма
    print("🔍 Перевірка доступності сервера...")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=2)
        if response.status_code == 200:
            print("  ✅ Сервер працює")
        else:
            print("  ❌ Сервер не відповідає коректно")
            return 1
    except requests.exceptions.ConnectionError:
        print("  ❌ Сервер не запущений!")
        print("  💡 Запустіть програму: python main.py --test-mode")
        return 1
    except Exception as e:
        print(f"  ❌ Помилка: {e}")
        return 1
    
    # Тести
    results = []
    
    results.append(("API ендпоінти", test_api_endpoints()))
    results.append(("Датчики", test_sensors()))
    results.append(("Стан системи", test_system_state()))
    results.append(("Веб-сторінки", test_web_pages()))
    
    # Підсумок
    print("\n" + "=" * 60)
    print("📊 Результати тестування:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ ПРОЙДЕНО" if result else "❌ НЕ ПРОЙДЕНО"
        print(f"  {status} - {name}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 Всі тести пройдено успішно!")
        return 0
    else:
        print("⚠️  Деякі тести не пройдено")
        return 1


if __name__ == '__main__':
    sys.exit(main())

