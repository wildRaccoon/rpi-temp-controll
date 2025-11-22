"""
Тестовий контролер Tapo для симуляції в тестовому режимі.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from utils.config_manager import ConfigManager
from utils.logger import get_logger


class TestTapoController:
    """Тестовий контролер Tapo для симуляції."""
    
    def __init__(self, config: ConfigManager):
        """
        Ініціалізація тестового контролера.
        
        Args:
            config: Об'єкт ConfigManager
        """
        self.config = config
        self.logger = get_logger()
        self.is_connected = True
        self.last_status: Optional[bool] = False
        self.last_update: Optional[datetime] = None
        self.command_history: list = []
        
        tapo_config = config.get_section('tapo')
        self.ip_address = tapo_config.get('ip_address', '192.168.1.100')
        
        self.logger.info(f"TestTapoController: ініціалізовано (тестовий режим, IP: {self.ip_address})")
    
    def connect(self) -> bool:
        """Симуляція підключення."""
        self.is_connected = True
        self.logger.info("TestTapoController: підключено (симуляція)")
        return True
    
    def turn_on(self) -> bool:
        """Симуляція вмикання розетки."""
        self.last_status = True
        self.last_update = datetime.now()
        self.command_history.append({
            'action': 'on',
            'timestamp': self.last_update.isoformat()
        })
        self.logger.info("TestTapoController: розетка увімкнена (симуляція)")
        return True
    
    def turn_off(self) -> bool:
        """Симуляція вимикання розетки."""
        self.last_status = False
        self.last_update = datetime.now()
        self.command_history.append({
            'action': 'off',
            'timestamp': self.last_update.isoformat()
        })
        self.logger.info("TestTapoController: розетка вимкнена (симуляція)")
        return True
    
    def get_status(self) -> Optional[bool]:
        """Отримати поточний стан (симуляція)."""
        return self.last_status
    
    def set_state(self, state: bool) -> bool:
        """Встановити стан розетки."""
        if state:
            return self.turn_on()
        else:
            return self.turn_off()
    
    def get_info(self) -> Dict[str, Any]:
        """Отримати інформацію про розетку."""
        return {
            'ip_address': self.ip_address,
            'connected': self.is_connected,
            'status': self.last_status,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'test_mode': True,
            'command_count': len(self.command_history)
        }
    
    def get_command_history(self) -> list:
        """Отримати історію команд (для тестування)."""
        return self.command_history.copy()

