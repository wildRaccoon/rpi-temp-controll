"""
Моделі даних для бази даних.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TemperatureReading:
    """Модель зчитування температури."""
    sensor_id: str
    temperature: float
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Конвертувати в словник."""
        return {
            'sensor_id': self.sensor_id,
            'temperature': self.temperature,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class OutletEvent:
    """Модель події вмикання/вимикання розетки."""
    action: str  # 'on' або 'off'
    reason: str  # Причина зміни стану
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Конвертувати в словник."""
        return {
            'action': self.action,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat()
        }

