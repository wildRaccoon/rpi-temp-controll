"""
Базовий клас для датчиків температури.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime


class BaseSensor(ABC):
    """Абстрактний базовий клас для всіх датчиків температури."""
    
    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any]):
        """
        Ініціалізація базового датчика.
        
        Args:
            sensor_id: Унікальний ідентифікатор датчика
            name: Назва датчика
            config: Конфігурація датчика
        """
        self.sensor_id = sensor_id
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', True)
        self.last_reading: Optional[float] = None
        self.last_update: Optional[datetime] = None
        self.error_count = 0
        self.max_errors = 3
    
    @abstractmethod
    def read_temperature(self) -> Optional[float]:
        """
        Зчитати температуру з датчика.
        
        Returns:
            Температура в градусах Цельсія або None при помилці
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Ініціалізувати датчик.
        
        Returns:
            True якщо ініціалізація успішна
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Отримати статус датчика.
        
        Returns:
            Словник зі статусом датчика
        """
        return {
            'id': self.sensor_id,
            'name': self.name,
            'type': self.__class__.__name__,
            'temperature': self.last_reading,
            'status': 'ok' if self.last_reading is not None else 'error',
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'enabled': self.enabled,
            'error_count': self.error_count
        }
    
    def is_available(self) -> bool:
        """
        Перевірити, чи доступний датчик.
        
        Returns:
            True якщо датчик доступний
        """
        return self.enabled and self.error_count < self.max_errors
    
    def reset_errors(self) -> None:
        """Скинути лічильник помилок."""
        self.error_count = 0
    
    def record_error(self) -> None:
        """Записати помилку зчитування."""
        self.error_count += 1

