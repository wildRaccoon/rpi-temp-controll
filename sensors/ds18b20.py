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
                self.sensor = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id=self.device_id)
            else:
                # Автоматичне визначення першого доступного датчика
                sensors = W1ThermSensor.get_available_sensors([Sensor.DS18B20])
                if not sensors:
                    self.logger.error(f"DS18B20 {self.name}: датчик не знайдено")
                    return False
                self.sensor = sensors[0]
                self.device_id = self.sensor.id
                self.logger.info(f"DS18B20 {self.name}: знайдено датчик з ID {self.device_id}")
            
            # Тестове зчитування
            temp = self.sensor.get_temperature()
            self.logger.info(f"DS18B20 {self.name}: ініціалізовано (ID: {self.device_id}, тест: {temp:.2f}°C)")
            return True
            
        except Exception as e:
            self.logger.error(f"DS18B20 {self.name}: помилка ініціалізації - {e}")
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

