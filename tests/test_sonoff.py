"""
Тестовий контролер Sonoff для симуляції в тестовому режимі.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from utils.config_manager import ConfigManager
from utils.logger import get_logger


class TestSonoffController:
    """Тестовий контролер Sonoff S60 для симуляції."""

    def __init__(self, config: ConfigManager):
        """
        Ініціалізація тестового контролера.

        Args:
            config: Об'єкт ConfigManager
        """
        self.config = config
        self.logger = get_logger()
        self.is_connected = True
        self.offline_mode = False
        self.last_status: Optional[bool] = False
        self.last_update: Optional[datetime] = None
        self.command_history: list = []

        sonoff_config = config.get_section('sonoff')
        self.ip_address = sonoff_config.get('ip_address', '192.168.1.100')

        self.logger.info(
            f"TestSonoffController: ініціалізовано (тестовий режим, IP: {self.ip_address})"
        )

    def connect(self) -> bool:
        """Симуляція підключення."""
        self.is_connected = True
        self.offline_mode = False
        self.logger.info("TestSonoffController: підключено (симуляція)")
        return True

    def turn_on(self) -> bool:
        """Симуляція вмикання розетки."""
        self.last_status = True
        self.last_update = datetime.now()
        self.command_history.append({
            'action': 'on',
            'timestamp': self.last_update.isoformat()
        })
        self.logger.info("TestSonoffController: розетка Sonoff увімкнена (симуляція)")
        return True

    def turn_off(self) -> bool:
        """Симуляція вимикання розетки."""
        self.last_status = False
        self.last_update = datetime.now()
        self.command_history.append({
            'action': 'off',
            'timestamp': self.last_update.isoformat()
        })
        self.logger.info("TestSonoffController: розетка Sonoff вимкнена (симуляція)")
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

    def toggle(self) -> bool:
        """Симуляція перемикання стану розетки."""
        new_state = not self.last_status if self.last_status is not None else True
        self.last_status = new_state
        self.last_update = datetime.now()
        self.command_history.append({
            'action': 'toggle',
            'new_state': 'on' if new_state else 'off',
            'timestamp': self.last_update.isoformat()
        })
        state_str = "увімкнена" if new_state else "вимкнена"
        self.logger.info(f"TestSonoffController: розетка Sonoff перемкнута, тепер {state_str} (симуляція)")
        return True

    def get_info(self) -> Dict[str, Any]:
        """Отримати інформацію про розетку."""
        return {
            'ip_address': self.ip_address,
            'connected': self.is_connected,
            'offline_mode': self.offline_mode,
            'status': self.last_status,
            'simulated': True,
            'device_type': 'sonoff_s60_tasmota',
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'test_mode': True,
            'command_count': len(self.command_history)
        }

    def get_device_info(self) -> Optional[Dict[str, Any]]:
        """Отримати детальну інформацію про пристрій (симуляція)."""
        return {
            'Status': {
                'Module': 1,
                'DeviceName': 'Sonoff_S60_Test',
                'FriendlyName': ['Test Sonoff'],
                'Topic': 'sonoff_s60_test'
            },
            'StatusNET': {
                'Hostname': 'sonoff-test',
                'IPAddress': self.ip_address,
                'Mac': '00:00:00:00:00:00'
            },
            'StatusFWR': {
                'Version': '13.0.0(tasmota)',
                'Hardware': 'ESP8266'
            }
        }

    def get_command_history(self) -> list:
        """Отримати історію команд (для тестування)."""
        return self.command_history.copy()
