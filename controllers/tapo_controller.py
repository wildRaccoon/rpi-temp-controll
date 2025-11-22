"""
Модуль для керування розумною розеткою Tapo.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

try:
    from tapo import ApiClient
    TAPO_AVAILABLE = True
except ImportError:
    TAPO_AVAILABLE = False

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
        self.client: Optional[Any] = None
        self.device: Optional[Any] = None
        self.ip_address: Optional[str] = None
        self.is_connected = False
        self.last_status: Optional[bool] = None
        self.last_update: Optional[datetime] = None

        tapo_config = config.get_section('tapo')
        self.ip_address = tapo_config.get('ip_address')
        self.email = tapo_config.get('email')
        self.password = tapo_config.get('password')

    def _run_async(self, coro):
        """
        Виконати асинхронну функцію в синхронному контексті.

        Args:
            coro: Coroutine для виконання

        Returns:
            Результат виконання coroutine
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Якщо цикл вже запущений, створюємо новий
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        except Exception as e:
            self.logger.error(f"Помилка виконання async операції: {e}")
            raise

    async def _connect_async(self) -> bool:
        """
        Асинхронно підключитися до розетки Tapo.

        Returns:
            True якщо підключення успішне
        """
        if not TAPO_AVAILABLE:
            self.logger.error(
                "tapo не встановлено. Встановіть: pip install tapo"
            )
            return False

        if not self.ip_address or not self.email or not self.password:
            self.logger.error("Не вказано IP адресу, email або пароль для Tapo")
            return False

        try:
            self.client = ApiClient(self.email, self.password)
            self.device = await self.client.p100(self.ip_address)
            self.is_connected = True
            self.logger.info(f"Підключено до розетки Tapo ({self.ip_address})")
            return True
        except Exception as e:
            self.logger.error(f"Помилка підключення до Tapo: {e}")
            self.is_connected = False
            return False

    def connect(self) -> bool:
        """
        Підключитися до розетки Tapo.

        Returns:
            True якщо підключення успішне
        """
        return self._run_async(self._connect_async())

    async def _turn_on_async(self) -> bool:
        """
        Асинхронно увімкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        if not self.is_connected:
            if not await self._connect_async():
                return False

        try:
            await self.device.on()
            self.last_status = True
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo увімкнена")
            return True
        except Exception as e:
            self.logger.error(f"Помилка вмикання розетки: {e}")
            self.is_connected = False
            return False

    def turn_on(self) -> bool:
        """
        Увімкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        return self._run_async(self._turn_on_async())

    async def _turn_off_async(self) -> bool:
        """
        Асинхронно вимкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        if not self.is_connected:
            if not await self._connect_async():
                return False

        try:
            await self.device.off()
            self.last_status = False
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo вимкнена")
            return True
        except Exception as e:
            self.logger.error(f"Помилка вимикання розетки: {e}")
            self.is_connected = False
            return False

    def turn_off(self) -> bool:
        """
        Вимкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        return self._run_async(self._turn_off_async())

    async def _get_status_async(self) -> Optional[bool]:
        """
        Асинхронно отримати поточний стан розетки.

        Returns:
            True якщо увімкнена, False якщо вимкнена, None при помилці
        """
        if not self.is_connected:
            if not await self._connect_async():
                return None

        try:
            device_info = await self.device.get_device_info()
            is_on = device_info.device_on
            self.last_status = is_on
            self.last_update = datetime.now()
            return is_on
        except Exception as e:
            self.logger.error(f"Помилка отримання статусу розетки: {e}")
            self.is_connected = False
            return None

    def get_status(self) -> Optional[bool]:
        """
        Отримати поточний стан розетки.

        Returns:
            True якщо увімкнена, False якщо вимкнена, None при помилці
        """
        return self._run_async(self._get_status_async())

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
