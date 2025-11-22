"""
Модуль для керування розумною розеткою Tapo.
"""

from typing import Optional, Dict, Any
from datetime import datetime

try:
    from PyP100 import P100
    P100_AVAILABLE = True
except ImportError:
    P100_AVAILABLE = False

from utils.config_manager import ConfigManager
from utils.logger import get_logger


class TapoController:
    """Клас для керування розеткою Tapo."""
    
    def __init__(self, config: ConfigManager):
        """
        Ініціалізація контролера Tapo.
        
        Args:
            config: Об'єкт ConfigManager
        """
        self.config = config
        self.logger = get_logger()
        self.device: Optional[P100] = None
        self.ip_address: Optional[str] = None
        self.is_connected = False
        self.last_status: Optional[bool] = None
        self.last_update: Optional[datetime] = None
        
        tapo_config = config.get_section('tapo')
        self.ip_address = tapo_config.get('ip_address')
        self.email = tapo_config.get('email')
        self.password = tapo_config.get('password')
    
    def connect(self) -> bool:
        """
        Підключитися до розетки Tapo.
        
        Returns:
            True якщо підключення успішне
        """
        if not P100_AVAILABLE:
            self.logger.error(
                "PyP100 не встановлено. Встановіть: pip install PyP100"
            )
            return False
        
        if not self.ip_address or not self.email or not self.password:
            self.logger.error("Не вказано IP адресу, email або пароль для Tapo")
            return False
        
        try:
            self.device = P100.P100(self.ip_address, self.email, self.password)
            self.device.handshake()
            self.device.login()
            self.is_connected = True
            self.logger.info(f"Підключено до розетки Tapo ({self.ip_address})")
            return True
        except Exception as e:
            self.logger.error(f"Помилка підключення до Tapo: {e}")
            self.is_connected = False
            return False
    
    def turn_on(self) -> bool:
        """
        Увімкнути розетку.
        
        Returns:
            True якщо команда виконана успішно
        """
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            self.device.turnOn()
            self.last_status = True
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo увімкнена")
            return True
        except Exception as e:
            self.logger.error(f"Помилка вмикання розетки: {e}")
            self.is_connected = False
            return False
    
    def turn_off(self) -> bool:
        """
        Вимкнути розетку.
        
        Returns:
            True якщо команда виконана успішно
        """
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            self.device.turnOff()
            self.last_status = False
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo вимкнена")
            return True
        except Exception as e:
            self.logger.error(f"Помилка вимикання розетки: {e}")
            self.is_connected = False
            return False
    
    def get_status(self) -> Optional[bool]:
        """
        Отримати поточний стан розетки.
        
        Returns:
            True якщо увімкнена, False якщо вимкнена, None при помилці
        """
        if not self.is_connected:
            if not self.connect():
                return None
        
        try:
            device_info = self.device.getDeviceInfo()
            is_on = device_info.get('device_on', False)
            self.last_status = is_on
            self.last_update = datetime.now()
            return is_on
        except Exception as e:
            self.logger.error(f"Помилка отримання статусу розетки: {e}")
            self.is_connected = False
            return None
    
    def set_state(self, state: bool) -> bool:
        """
        Встановити стан розетки.
        
        Args:
            state: True для вмикання, False для вимикання
        
        Returns:
            True якщо команда виконана успішно
        """
        if state:
            return self.turn_on()
        else:
            return self.turn_off()
    
    def get_info(self) -> Dict[str, Any]:
        """
        Отримати інформацію про розетку.
        
        Returns:
            Словник з інформацією про розетку
        """
        return {
            'ip_address': self.ip_address,
            'connected': self.is_connected,
            'status': self.last_status,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

