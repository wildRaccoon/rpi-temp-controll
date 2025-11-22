#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простий тест для перевірки що сервіс працює.
"""

import sys
import time
import requests
from pathlib import Path

# Налаштування кодування для Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Додати батьківську директорію до шляху
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_manager import ConfigManager
from sensors.sensor_manager import SensorManager
from controllers.tapo_controller import TapoController
from controllers.temperature_controller import TemperatureController

def test_components():
    """Тест окремих компонентів."""
    print("="*60)
    print("Тест компонентів системи")
    print("="*60)

    # 1. Config
    print("\n1. Завантаження конфігурації...")
    try:
        config = ConfigManager("config.yaml")
        print("   ✓ Конфігурація завантажена")
    except Exception as e:
        print(f"   ✗ Помилка: {e}")
        return False

    # 2. Sensors
    print("\n2. Ініціалізація датчиків...")
    try:
        sensor_manager = SensorManager(config)
        temps = sensor_manager.read_all()
        print(f"   ✓ Датчиків: {len(sensor_manager.sensors)}")
        for sensor_id, temp in temps.items():
            if temp is not None:
                print(f"     - {sensor_id}: {temp:.1f}°C")
    except Exception as e:
        print(f"   ✗ Помилка: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 3. Tapo Controller
    print("\n3. Ініціалізація контролера розетки...")
    try:
        tapo = TapoController(config)
        print(f"   ✓ TapoController створено")
        print(f"     IP: {tapo.ip_address}")
        print(f"     Offline mode: {tapo.offline_mode}")

        # Тест get_status
        status = tapo.get_status()
        print(f"     Статус: {status}")
        print(f"   ✓ get_status() працює")

        # Тест turn_on
        tapo.turn_on()
        print(f"   ✓ turn_on() працює")

        # Тест turn_off
        tapo.turn_off()
        print(f"   ✓ turn_off() працює")

    except Exception as e:
        print(f"   ✗ Помилка: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 4. Temperature Controller
    print("\n4. Ініціалізація контролера температури...")
    try:
        temp_ctrl = TemperatureController(sensor_manager, tapo, config)
        system_state = temp_ctrl.get_system_state()
        print(f"   ✓ TemperatureController створено")
        print(f"     Стан системи: {system_state['state']}")
        print(f"     Котел: {system_state['boiler_temp']}°C")
        print(f"     Розетка: {system_state['outlet_status']}")
    except Exception as e:
        print(f"   ✗ Помилка: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*60)
    print("✅ Всі компоненти працюють!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_components()
    sys.exit(0 if success else 1)
