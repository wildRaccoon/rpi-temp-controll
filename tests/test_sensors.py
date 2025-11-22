"""
Тестові датчики для симуляції в тестовому режимі.
"""

import random
from typing import Optional, Dict, Any
from datetime import datetime

from sensors.base import BaseSensor
from utils.logger import get_logger


class TestDS18B20Sensor(BaseSensor):
    """Тестовий датчик DS18B20 для симуляції."""
    
    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any], base_temp: float = 20.0):
        """
        Ініціалізація тестового датчика.
        
        Args:
            sensor_id: Унікальний ідентифікатор датчика
            name: Назва датчика
            config: Конфігурація датчика
            base_temp: Базова температура для симуляції
        """
        super().__init__(sensor_id, name, config)
        self.base_temp = base_temp
        self.variation = config.get('variation_range', 2.0)
        self.variation_enabled = config.get('temperature_variation', True)
        self.logger = get_logger()
    
    def initialize(self) -> bool:
        """Ініціалізувати тестовий датчик."""
        self.logger.info(f"TestDS18B20 {self.name}: ініціалізовано (тестовий режим, базова темп: {self.base_temp}°C)")
        return True
    
    def read_temperature(self) -> Optional[float]:
        """Зчитати симульовану температуру."""
        if not self.enabled:
            return None
        
        if self.variation_enabled:
            # Додати випадкову варіацію
            variation = random.uniform(-self.variation, self.variation)
            temperature = self.base_temp + variation
        else:
            temperature = self.base_temp
        
        self.last_reading = temperature
        self.last_update = datetime.now()
        return temperature
    
    def set_temperature(self, temp: float) -> None:
        """Встановити температуру для тестування."""
        self.base_temp = temp


class TestMAX31855Sensor(BaseSensor):
    """Тестовий датчик MAX31855 для симуляції."""
    
    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any], base_temp: float = 150.0):
        """
        Ініціалізація тестового датчика.
        
        Args:
            sensor_id: Унікальний ідентифікатор датчика
            name: Назва датчика
            config: Конфігурація датчика
            base_temp: Базова температура для симуляції
        """
        super().__init__(sensor_id, name, config)
        self.base_temp = base_temp
        self.variation = config.get('variation_range', 5.0)
        self.variation_enabled = config.get('temperature_variation', True)
        self.logger = get_logger()
    
    def initialize(self) -> bool:
        """Ініціалізувати тестовий датчик."""
        self.logger.info(f"TestMAX31855 {self.name}: ініціалізовано (тестовий режим, базова темп: {self.base_temp}°C)")
        return True
    
    def read_temperature(self) -> Optional[float]:
        """Зчитати симульовану температуру."""
        if not self.enabled:
            return None
        
        if self.variation_enabled:
            # Додати випадкову варіацію
            variation = random.uniform(-self.variation, self.variation)
            temperature = self.base_temp + variation
        else:
            temperature = self.base_temp
        
        self.last_reading = temperature
        self.last_update = datetime.now()
        return temperature
    
    def set_temperature(self, temp: float) -> None:
        """Встановити температуру для тестування."""
        self.base_temp = temp

