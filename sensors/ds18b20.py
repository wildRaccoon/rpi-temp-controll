"""
Модуль для роботи з датчиком температури DS18B20 (1-Wire).
"""

from typing import Optional, Dict, Any
from datetime import datetime
import time

try:
    from w1thermsensor import W1ThermSensor, Sensor
    W1_AVAILABLE = True
except ImportError:
    W1_AVAILABLE = False

from sensors.base import BaseSensor
from utils.logger import get_logger


class DS18B20Sensor(BaseSensor):
    """Клас для роботи з датчиком DS18B20."""
    
    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any]):
        """
        Ініціалізація датчика DS18B20.
        
        Args:
            sensor_id: Унікальний ідентифікатор датчика
            name: Назва датчика
            config: Конфігурація датчика (device_id, enabled, name)
        """
        super().__init__(sensor_id, name, config)
        self.device_id = config.get('device_id')
        self.sensor: Optional[W1ThermSensor] = None
        self.logger = get_logger()
    
    def initialize(self) -> bool:
        """
        Ініціалізувати датчик DS18B20.
        
        Примітка: Всі DS18B20 датчики підключені до однієї 1-Wire шини (GPIO 4).
        Кожен датчик ідентифікується за унікальним device_id.
        
        Returns:
            True якщо ініціалізація успішна
        """
        if not W1_AVAILABLE:
            self.logger.warning(
                f"DS18B20: w1thermsensor не встановлено. "
                f"Встановіть: pip install w1thermsensor"
            )
            return False
        
        if not self.enabled:
            self.logger.info(f"DS18B20 {self.name}: вимкнено в конфігурації")
            return False
        
        try:
            if self.device_id:
                # Використати конкретний device_id
                # Всі датчики на одній 1-Wire шині, але мають різні ID
                self.sensor = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id=self.device_id)
                self.logger.info(
                    f"DS18B20 {self.name}: використовується датчик з ID {self.device_id} "
                    f"(1-Wire шина GPIO 4)"
                )
            else:
                # Автоматичне визначення - знайти всі доступні датчики на 1-Wire шині
                sensors = W1ThermSensor.get_available_sensors([Sensor.DS18B20])
                if not sensors:
                    self.logger.error(
                        f"DS18B20 {self.name}: датчики не знайдено на 1-Wire шині (GPIO 4). "
                        f"Перевірте підключення та увімкнення 1-Wire інтерфейсу."
                    )
                    return False
                
                # Якщо знайдено кілька датчиків, використати перший
                # Але краще вказати device_id в конфігурації
                if len(sensors) > 1:
                    self.logger.warning(
                        f"DS18B20 {self.name}: знайдено {len(sensors)} датчиків на 1-Wire шині. "
                        f"Рекомендується вказати device_id в конфігурації для коректної роботи."
                    )
                
                self.sensor = sensors[0]
                self.device_id = self.sensor.id
                self.logger.info(
                    f"DS18B20 {self.name}: автоматично знайдено датчик з ID {self.device_id} "
                    f"на 1-Wire шині (GPIO 4)"
                )
            
            # Тестове зчитування
            temp = self.sensor.get_temperature()
            self.logger.info(
                f"DS18B20 {self.name}: ініціалізовано успішно "
                f"(ID: {self.device_id}, тест: {temp:.2f}°C, 1-Wire шина GPIO 4)"
            )
            return True
            
        except Exception as e:
            self.logger.error(
                f"DS18B20 {self.name}: помилка ініціалізації - {e}. "
                f"Перевірте підключення до 1-Wire шини (GPIO 4) та наявність device_id."
            )
            return False
    
    def read_temperature(self) -> Optional[float]:
        """
        Зчитати температуру з датчика DS18B20.
        
        Returns:
            Температура в градусах Цельсія або None при помилці
        """
        if not self.enabled or not self.sensor:
            return None
        
        try:
            temperature = self.sensor.get_temperature()
            self.last_reading = temperature
            self.last_update = datetime.now()
            self.reset_errors()
            return temperature
            
        except Exception as e:
            self.logger.error(f"DS18B20 {self.name}: помилка зчитування - {e}")
            self.record_error()
            return None

