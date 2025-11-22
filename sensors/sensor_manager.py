"""
Менеджер для управління всіма датчиками.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from sensors.base import BaseSensor
try:
    from sensors.ds18b20 import DS18B20Sensor
    DS18B20_AVAILABLE = True
except Exception:
    DS18B20_AVAILABLE = False

try:
    from sensors.max31855 import MAX31855Sensor
    MAX31855_AVAILABLE = True
except Exception:
    MAX31855_AVAILABLE = False

from tests.test_sensors import TestDS18B20Sensor, TestMAX31855Sensor
from utils.config_manager import ConfigManager
from utils.logger import get_logger


class SensorManager:
    """Клас для управління всіма датчиками температури."""
    
    def __init__(self, config: ConfigManager):
        """
        Ініціалізація менеджера датчиків.
        
        Args:
            config: Об'єкт ConfigManager
        """
        self.config = config
        self.logger = get_logger()
        self.sensors: Dict[str, BaseSensor] = {}
        self.is_test_mode = config.is_test_mode()
        self._initialize_sensors()
    
    def _initialize_sensors(self) -> None:
        """
        Ініціалізувати всі датчики з конфігурації.
        
        Примітка: Всі DS18B20 датчики підключені до однієї 1-Wire шини (GPIO 4).
        Кожен датчик ідентифікується за унікальним device_id.
        """
        sensors_config = self.config.get_section('sensors')
        
        # Ініціалізувати DS18B20 датчики
        # Всі датчики на одній 1-Wire шині, але мають різні device_id
        ds18b20_config = sensors_config.get('ds18b20', {})
        
        if not self.is_test_mode and ds18b20_config:
            # У production режимі можна показати всі доступні датчики на шині
            try:
                from w1thermsensor import W1ThermSensor, Sensor
                available_sensors = W1ThermSensor.get_available_sensors([Sensor.DS18B20])
                if available_sensors:
                    self.logger.info(
                        f"Знайдено {len(available_sensors)} DS18B20 датчик(ів) на 1-Wire шині (GPIO 4):"
                    )
                    for s in available_sensors:
                        self.logger.info(f"  - ID: {s.id}")
            except:
                pass
        
        for sensor_key, sensor_config in ds18b20_config.items():
            if sensor_config.get('enabled', False):
                sensor_id = f"ds18b20_{sensor_key}"
                name = sensor_config.get('name', sensor_key)
                
                if self.is_test_mode:
                    # Тестовий режим
                    test_temps = self.config.get_test_temperatures()
                    base_temp = test_temps.get(sensor_key, 20.0)
                    sensor = TestDS18B20Sensor(sensor_id, name, sensor_config, base_temp)
                elif DS18B20_AVAILABLE:
                    # Production режим - всі датчики на одній 1-Wire шині
                    sensor = DS18B20Sensor(sensor_id, name, sensor_config)
                else:
                    self.logger.warning(f"DS18B20 недоступний (Windows або немає модулів ядра). Використовую тестовий датчик для {sensor_id}")
                    test_temps = self.config.get_test_temperatures()
                    base_temp = test_temps.get(sensor_key, 20.0)
                    sensor = TestDS18B20Sensor(sensor_id, name, sensor_config, base_temp)
                
                if sensor.initialize():
                    self.sensors[sensor_id] = sensor
                    self.logger.info(f"Датчик {sensor_id} ({name}) ініціалізовано на 1-Wire шині")
                else:
                    self.logger.error(f"Не вдалося ініціалізувати датчик {sensor_id}")
        
        # Ініціалізувати MAX31855 датчики
        max31855_config = sensors_config.get('max31855', {})
        for sensor_key, sensor_config in max31855_config.items():
            if sensor_config.get('enabled', False):
                sensor_id = f"max31855_{sensor_key}"
                name = sensor_config.get('name', sensor_key)
                
                if self.is_test_mode:
                    # Тестовий режим
                    test_temps = self.config.get_test_temperatures()
                    base_temp = test_temps.get(sensor_key, 150.0)
                    sensor = TestMAX31855Sensor(sensor_id, name, sensor_config, base_temp)
                elif MAX31855_AVAILABLE:
                    # Production режим
                    sensor = MAX31855Sensor(sensor_id, name, sensor_config)
                else:
                    self.logger.warning(f"MAX31855 недоступний (Windows або немає spidev). Використовую тестовий датчик для {sensor_id}")
                    test_temps = self.config.get_test_temperatures()
                    base_temp = test_temps.get(sensor_key, 150.0)
                    sensor = TestMAX31855Sensor(sensor_id, name, sensor_config, base_temp)
                
                if sensor.initialize():
                    self.sensors[sensor_id] = sensor
                    self.logger.info(f"Датчик {sensor_id} ({name}) ініціалізовано")
                else:
                    self.logger.error(f"Не вдалося ініціалізувати датчик {sensor_id}")
    
    def read_all(self) -> Dict[str, Optional[float]]:
        """
        Зчитати температури з усіх датчиків.
        
        Returns:
            Словник {sensor_id: temperature}
        """
        readings = {}
        for sensor_id, sensor in self.sensors.items():
            if sensor.is_available():
                readings[sensor_id] = sensor.read_temperature()
            else:
                readings[sensor_id] = None
        return readings
    
    def get_sensor(self, sensor_id: str) -> Optional[BaseSensor]:
        """
        Отримати датчик за ID.
        
        Args:
            sensor_id: ID датчика
        
        Returns:
            Об'єкт датчика або None
        """
        return self.sensors.get(sensor_id)
    
    def get_all_status(self) -> List[Dict[str, Any]]:
        """
        Отримати статуси всіх датчиків.
        
        Returns:
            Список словників зі статусами датчиків
        """
        return [sensor.get_status() for sensor in self.sensors.values()]
    
    def get_temperature(self, sensor_id: str) -> Optional[float]:
        """
        Отримати температуру конкретного датчика.
        
        Args:
            sensor_id: ID датчика
        
        Returns:
            Температура або None
        """
        sensor = self.get_sensor(sensor_id)
        if sensor:
            return sensor.read_temperature()
        return None

