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

        # Режим роботи без розетки (симуляція)
        self.offline_mode = False
        self.simulated_state: bool = False

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
            # Спробувати отримати поточний event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # Немає запущеного loop - створити новий
                loop = None

            if loop and loop.is_running():
                # Loop вже запущений (наприклад, в async контексті)
                # Не можна викликати run_until_complete
                # Створюємо новий loop в окремому потоці
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                # Немає запущеного loop або він не запущений
                # Використовуємо asyncio.run (рекомендований спосіб для Python 3.7+)
                return asyncio.run(coro)
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
            self.logger.warning(
                "tapo не встановлено. Працюю в режимі офлайн (без розетки)"
            )
            self.offline_mode = True
            return False

        if not self.ip_address or not self.email or not self.password:
            self.logger.warning("Не вказано креденшли для Tapo. Працюю в режимі офлайн")
            self.offline_mode = True
            return False

        try:
            self.client = ApiClient(self.email, self.password)
            self.device = await self.client.p100(self.ip_address)
            self.is_connected = True
            self.offline_mode = False
            self.logger.info(f"Підключено до розетки Tapo ({self.ip_address})")
            return True
        except Exception as e:
            self.logger.warning(f"Помилка підключення до Tapo: {e}. Працюю в режимі офлайн (без розетки)")
            self.is_connected = False
            self.offline_mode = True
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
                # Режим офлайн - симулюємо вмикання
                if self.offline_mode:
                    self.simulated_state = True
                    self.last_status = True
                    self.last_update = datetime.now()
                    self.logger.info("Розетка Tapo [СИМУЛЯЦІЯ]: увімкнена")
                    return True
                return False

        try:
            await self.device.on()
            self.last_status = True
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo увімкнена")
            return True
        except Exception as e:
            self.logger.warning(f"Помилка вмикання розетки: {e}. Переходжу в режим офлайн")
            self.is_connected = False
            self.offline_mode = True
            # Симулюємо вмикання
            self.simulated_state = True
            self.last_status = True
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo [СИМУЛЯЦІЯ]: увімкнена")
            return True

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
                # Режим офлайн - симулюємо вимкнення
                if self.offline_mode:
                    self.simulated_state = False
                    self.last_status = False
                    self.last_update = datetime.now()
                    self.logger.info("Розетка Tapo [СИМУЛЯЦІЯ]: вимкнена")
                    return True
                return False

        try:
            await self.device.off()
            self.last_status = False
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo вимкнена")
            return True
        except Exception as e:
            self.logger.warning(f"Помилка вимикання розетки: {e}. Переходжу в режим офлайн")
            self.is_connected = False
            self.offline_mode = True
            # Симулюємо вимкнення
            self.simulated_state = False
            self.last_status = False
            self.last_update = datetime.now()
            self.logger.info("Розетка Tapo [СИМУЛЯЦІЯ]: вимкнена")
            return True

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
                # Режим офлайн - повертаємо симульований стан
                if self.offline_mode:
                    return self.simulated_state
                return None

        try:
            device_info = await self.device.get_device_info()
            is_on = device_info.device_on
            self.last_status = is_on
            self.last_update = datetime.now()
            return is_on
        except Exception as e:
            self.logger.warning(f"Помилка отримання статусу розетки: {e}. Використовую останній відомий стан")
            self.is_connected = False
            self.offline_mode = True
            # Повертаємо останній відомий стан
            return self.last_status if self.last_status is not None else self.simulated_state

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
            'offline_mode': self.offline_mode,
            'status': self.last_status,
            'simulated': self.offline_mode,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }
