"""
Головний файл програми контролю температури для твердопаливного котла.
"""

import argparse
import signal
import sys
import time
from datetime import datetime, timedelta
from threading import Event

from utils.config_manager import ConfigManager
from utils.logger import Logger
from sensors.sensor_manager import SensorManager
from controllers.tapo_controller import TapoController
from tests.test_tapo import TestTapoController
from controllers.temperature_controller import TemperatureController
from database.db import Database
from api.server import APIServer


class TemperatureControlApp:
    """Головний клас програми."""
    
    def __init__(self, config_path: str = "config.yaml", test_mode: bool = False, test_scenario: str = None):
        """
        Ініціалізація програми.
        
        Args:
            config_path: Шлях до файлу конфігурації
            test_mode: Чи запускати в тестовому режимі
            test_scenario: Тестовий сценарій
        """
        # Завантаження конфігурації
        self.config = ConfigManager(config_path)
        
        # Перевизначити тестовий режим, якщо вказано в аргументах
        if test_mode:
            test_mode_config = self.config.get_section('test_mode')
            test_mode_config['enabled'] = True
            if test_scenario:
                test_mode_config['scenario'] = test_scenario
        
        # Налаштування логування
        log_config = self.config.get_section('logging')
        logger = Logger()
        logger.setup(
            log_file=log_config.get('log_file', 'logs/temperature.log'),
            log_level=10 if self.config.get('api.debug', False) else 20,
            enable_console=True
        )
        self.logger = logger.get_logger()
        
        # Валідація конфігурації
        try:
            self.config.validate()
        except ValueError as e:
            self.logger.error(f"Помилка валідації конфігурації: {e}")
            sys.exit(1)
        
        # Ініціалізація компонентів
        self.logger.info("Ініціалізація компонентів...")
        
        # База даних
        db_config = self.config.get_section('database')
        self.database = Database(db_config.get('db_file', 'data/temperature.db'))
        
        # Менеджер датчиків
        self.sensor_manager = SensorManager(self.config)
        
        # Контролер розетки
        if self.config.is_test_mode():
            self.tapo_controller = TestTapoController(self.config)
        else:
            self.tapo_controller = TapoController(self.config)
            if not self.tapo_controller.connect():
                self.logger.warning("Не вдалося підключитися до розетки Tapo, продовжуємо...")
        
        # Контролер температури
        self.temperature_controller = TemperatureController(
            self.sensor_manager,
            self.tapo_controller,
            self.config
        )
        
        # API сервер
        api_config = self.config.get_section('api')
        if api_config.get('enabled', True):
            self.api_server = APIServer(
                self.sensor_manager,
                self.temperature_controller,
                self.database,
                self.config
            )
        else:
            self.api_server = None
        
        # Прапорець для завершення
        self.shutdown_event = Event()
        
        # Обробка сигналів
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Ініціалізація завершена")
    
    def _signal_handler(self, signum, frame):
        """Обробник сигналів для коректного завершення."""
        self.logger.info(f"Отримано сигнал {signum}, завершення роботи...")
        self.shutdown_event.set()
    
    def _apply_test_scenario(self, scenario: str) -> None:
        """Застосувати тестовий сценарій."""
        if not self.config.is_test_mode():
            return
        
        # Отримати тестові датчики
        test_temps = {
            'normal': {
                'boiler': 72.0,
                'accumulator_bottom': 68.0,
                'accumulator_top': 70.0,
                'chimney': 160.0
            },
            'critical': {
                'boiler': 87.0,
                'accumulator_bottom': 82.0,
                'accumulator_top': 85.0,
                'chimney': 220.0
            },
            'cooling': {
                'boiler': 55.0,
                'accumulator_bottom': 50.0,
                'accumulator_top': 52.0,
                'chimney': 90.0
            },
            'startup': {
                'boiler': 35.0,
                'accumulator_bottom': 30.0,
                'accumulator_top': 32.0,
                'chimney': 120.0
            }
        }
        
        temps = test_temps.get(scenario, test_temps['normal'])
        
        # Встановити температури для тестових датчиків
        for sensor_id, sensor in self.sensor_manager.sensors.items():
            if hasattr(sensor, 'set_temperature'):
                if 'boiler' in sensor_id:
                    sensor.set_temperature(temps['boiler'])
                elif 'accumulator_bottom' in sensor_id:
                    sensor.set_temperature(temps['accumulator_bottom'])
                elif 'accumulator_top' in sensor_id:
                    sensor.set_temperature(temps['accumulator_top'])
                elif 'chimney' in sensor_id:
                    sensor.set_temperature(temps['chimney'])
        
        self.logger.info(f"Застосовано тестовий сценарій: {scenario}")
    
    def _cleanup_database(self) -> None:
        """Очистити старі дані з бази."""
        db_config = self.config.get_section('database')
        retention_days = db_config.get('retention_days', 7)
        self.database.cleanup_old_data(retention_days)
    
    def run(self) -> None:
        """Запустити головний цикл програми."""
        self.logger.info("Запуск програми контролю температури")
        
        if self.config.is_test_mode():
            self.logger.info("⚠️  ТЕСТОВИЙ РЕЖИМ - реальні датчики та розетка не використовуються")
            scenario = self.config.get_test_scenario()
            if scenario:
                self._apply_test_scenario(scenario)
        
        # Запуск API сервера
        if self.api_server:
            self.api_server.start()
            time.sleep(1)  # Дати час серверу запуститися
        
        # Налаштування інтервалів
        control_config = self.config.get_section('control')
        check_interval = control_config.get('check_interval', 30)
        log_config = self.config.get_section('logging')
        log_interval = log_config.get('log_interval', 300)
        db_config = self.config.get_section('database')
        cleanup_interval = db_config.get('cleanup_interval', 3600)
        
        last_log_time = datetime.now()
        last_cleanup_time = datetime.now()
        last_outlet_state = None
        
        try:
            while not self.shutdown_event.is_set():
                # Зчитування температур
                temperatures = self.temperature_controller.get_temperatures()
                
                # Збереження в базу даних
                for sensor_id, temp in temperatures.items():
                    if temp is not None:
                        self.database.save_temperature_reading(sensor_id, temp)
                
                # Оновлення контролю
                outlet_reason = self.temperature_controller.update_control()
                
                # Збереження події розетки, якщо стан змінився
                current_outlet_state = self.temperature_controller.tapo_controller.get_status()
                if current_outlet_state != last_outlet_state and outlet_reason:
                    action = 'on' if current_outlet_state else 'off'
                    self.database.save_outlet_event(action, outlet_reason)
                    last_outlet_state = current_outlet_state
                
                # Логування (періодично)
                now = datetime.now()
                if (now - last_log_time).total_seconds() >= log_interval:
                    system_state = self.temperature_controller.get_system_state()

                    # Форматування температур з обробкою None
                    boiler_str = f"{system_state['boiler_temp']:.1f}°C" if system_state['boiler_temp'] is not None else "N/A"
                    accum_str = f"{system_state['accumulator_top_temp']:.1f}°C" if system_state['accumulator_top_temp'] is not None else "N/A"
                    chimney_str = f"{system_state['chimney_temp']:.1f}°C" if system_state['chimney_temp'] is not None else "N/A"

                    self.logger.info(
                        f"Статус: котел={boiler_str}, "
                        f"термоак={accum_str}, "
                        f"димар={chimney_str}, "
                        f"розетка={system_state['outlet_status']}"
                    )
                    last_log_time = now
                
                # Очищення бази даних (періодично)
                if (now - last_cleanup_time).total_seconds() >= cleanup_interval:
                    self._cleanup_database()
                    last_cleanup_time = now
                
                # Очікування до наступної перевірки
                self.shutdown_event.wait(check_interval)
        
        except KeyboardInterrupt:
            self.logger.info("Отримано сигнал переривання")
        except Exception as e:
            self.logger.critical(f"Критична помилка: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """Коректне завершення програми."""
        self.logger.info("Завершення роботи програми...")
        
        # Зупинити API сервер
        if self.api_server:
            self.api_server.stop()
        
        # Безпечно вимкнути розетку (опціонально)
        # self.tapo_controller.turn_off()
        
        self.logger.info("Програма завершена")


def main():
    """Головна функція."""
    parser = argparse.ArgumentParser(description='Система контролю температури для твердопаливного котла')
    parser.add_argument('--config', '-c', default='config.yaml', help='Шлях до файлу конфігурації')
    parser.add_argument('--test-mode', action='store_true', help='Запустити в тестовому режимі')
    parser.add_argument('--scenario', choices=['normal', 'critical', 'cooling', 'startup'],
                       help='Тестовий сценарій (тільки для тестового режиму)')
    
    args = parser.parse_args()
    
    app = TemperatureControlApp(
        config_path=args.config,
        test_mode=args.test_mode,
        test_scenario=args.scenario
    )
    
    app.run()


if __name__ == '__main__':
    main()

