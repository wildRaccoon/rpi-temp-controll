"""
Тест всіх сценаріїв роботи системи.
Послідовно запускає всі тестові сценарії та перевіряє правильність логіки.
"""

import sys
import time
import requests
import subprocess
import signal
from datetime import datetime

BASE_URL = "http://localhost:8080"
SCENARIOS = ["normal", "critical", "cooling", "startup"]
SCENARIO_DURATION = 120  # 2 хвилини на сценарій


def wait_for_server(timeout=30):
    """Чекати поки сервер стане доступним."""
    print("⏳ Очікування запуску сервера...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BASE_URL}/api/status", timeout=2)
            if response.status_code == 200:
                print("  ✅ Сервер запущено")
                time.sleep(2)  # Дати час на ініціалізацію
                return True
        except:
            pass
        time.sleep(1)
    
    print("  ❌ Сервер не запустився")
    return False


def check_scenario_conditions(scenario):
    """Перевірити умови для конкретного сценарію."""
    try:
        response = requests.get(f"{BASE_URL}/api/system", timeout=5)
        if response.status_code != 200:
            return False
        
        data = response.json()
        boiler_temp = data.get('boiler_temp')
        outlet_status = data.get('outlet_status')
        
        expected_conditions = {
            'normal': {
                'boiler_range': (70, 75),
                'outlet': 'off'
            },
            'critical': {
                'boiler_range': (85, 90),
                'outlet': 'on'
            },
            'cooling': {
                'boiler_range': (50, 60),
                'outlet': 'off'
            },
            'startup': {
                'boiler_range': (30, 40),
                'outlet': 'on'
            }
        }
        
        conditions = expected_conditions.get(scenario, {})
        boiler_range = conditions.get('boiler_range', (0, 100))
        expected_outlet = conditions.get('outlet', 'off')
        
        # Перевірка температури
        if boiler_temp:
            temp_ok = boiler_range[0] <= boiler_temp <= boiler_range[1]
        else:
            temp_ok = False
        
        # Перевірка розетки
        outlet_ok = outlet_status == expected_outlet
        
        return temp_ok and outlet_ok
        
    except Exception as e:
        print(f"    ❌ Помилка перевірки: {e}")
        return False


def test_scenario(scenario):
    """Протестувати конкретний сценарій."""
    print(f"\n{'=' * 60}")
    print(f"🧪 Тестування сценарію: {scenario.upper()}")
    print(f"{'=' * 60}")
    
    # Запустити програму з сценарієм
    print(f"🚀 Запуск програми з сценарієм '{scenario}'...")
    process = subprocess.Popen(
        [sys.executable, "main.py", "--test-mode", "--scenario", scenario],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Чекати запуску сервера
        if not wait_for_server():
            process.terminate()
            return False
        
        # Перевірити умови кілька разів
        print(f"⏱️  Моніторинг протягом {SCENARIO_DURATION} секунд...")
        checks_passed = 0
        total_checks = 5
        
        for i in range(total_checks):
            time.sleep(SCENARIO_DURATION // total_checks)
            if check_scenario_conditions(scenario):
                checks_passed += 1
                print(f"  ✅ Перевірка {i+1}/{total_checks} - OK")
            else:
                print(f"  ⚠️  Перевірка {i+1}/{total_checks} - не відповідає очікуванням")
        
        # Отримати фінальний стан
        response = requests.get(f"{BASE_URL}/api/system", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"\n📊 Фінальний стан:")
            print(f"  - Котел: {data.get('boiler_temp', 'N/A')}°C")
            print(f"  - Розетка: {data.get('outlet_status')}")
            print(f"  - Причина: {data.get('outlet_reason', 'N/A')}")
        
        # Результат
        success_rate = checks_passed / total_checks
        if success_rate >= 0.6:  # 60% перевірок пройдено
            print(f"\n✅ Сценарій '{scenario}' пройдено ({checks_passed}/{total_checks} перевірок)")
            return True
        else:
            print(f"\n❌ Сценарій '{scenario}' не пройдено ({checks_passed}/{total_checks} перевірок)")
            return False
            
    finally:
        # Зупинити процес
        print("🛑 Зупинка програми...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        time.sleep(2)


def main():
    """Головна функція тестування сценаріїв."""
    print("=" * 60)
    print("🧪 Тестування всіх сценаріїв системи контролю температури")
    print("=" * 60)
    print(f"📋 Сценарії: {', '.join(SCENARIOS)}")
    print(f"⏱️  Час на сценарій: {SCENARIO_DURATION} секунд")
    print()
    
    results = {}
    
    for scenario in SCENARIOS:
        results[scenario] = test_scenario(scenario)
        time.sleep(3)  # Пауза між сценаріями
    
    # Підсумок
    print("\n" + "=" * 60)
    print("📊 Підсумок тестування:")
    print("=" * 60)
    
    for scenario, result in results.items():
        status = "✅ ПРОЙДЕНО" if result else "❌ НЕ ПРОЙДЕНО"
        print(f"  {status} - {scenario}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\n📈 Результат: {passed}/{total} сценаріїв пройдено")
    
    if passed == total:
        print("🎉 Всі сценарії пройдено успішно!")
        return 0
    else:
        print("⚠️  Деякі сценарії не пройдено")
        return 1


if __name__ == '__main__':
    sys.exit(main())

