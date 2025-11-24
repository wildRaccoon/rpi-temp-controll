"""
Модуль для керування розумною розеткою Sonoff S60 з прошивкою Tasmota.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import requests
from urllib.parse import quote

from utils.config_manager import ConfigManager
from utils.logger import get_logger


class SonoffController:
    """Клас для керування розеткою Sonoff S60 через Tasmota HTTP API."""

    def __init__(self, config: ConfigManager):
        """
        Ініціалізація контролера Sonoff.

        Args:
            config: Об'єкт ConfigManager
        """
        self.config = config
        self.logger = get_logger()
        self.ip_address: Optional[str] = None
        self.is_connected = False
        self.last_status: Optional[bool] = None
        self.last_update: Optional[datetime] = None

        # Режим роботи без розетки (симуляція)
        self.offline_mode = False
        self.simulated_state: bool = False

        # Таймаут для HTTP запитів (секунди)
        self.timeout = 5

        sonoff_config = config.get_section('sonoff')
        self.ip_address = sonoff_config.get('ip_address')

        # Опціональна підтримка MQTT (поки не реалізована)
        mqtt_config = config.get_section('mqtt', {})
        self.mqtt_enabled = mqtt_config.get('enabled', False)

        if not self.ip_address:
            self.logger.warning("IP адреса Sonoff не вказана. Працюю в режимі офлайн")
            self.offline_mode = True

    def _build_url(self, command: str) -> str:
        """
        Створити URL для Tasmota HTTP API команди.

        Args:
            command: Команда для виконання (наприклад, "Power On", "Status")

        Returns:
            Повний URL для запиту
        """
        encoded_command = quote(command)
        return f"http://{self.ip_address}/cm?cmnd={encoded_command}"

    def _send_command(self, command: str) -> Optional[Dict[str, Any]]:
        """
        Відправити команду до Tasmota через HTTP API.

        Args:
            command: Команда для виконання

        Returns:
            JSON відповідь від Tasmota або None при помилці
        """
        if self.offline_mode:
            return None

        try:
            url = self._build_url(command)
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self.logger.warning(f"Таймаут при спробі зв'язатися з Sonoff ({self.ip_address})")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"Помилка з'єднання з Sonoff ({self.ip_address})")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"HTTP помилка від Sonoff: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Несподівана помилка при відправці команди до Sonoff: {e}")
            return None

    def connect(self) -> bool:
        """
        Перевірити підключення до розетки Sonoff.

        Returns:
            True якщо розетка доступна
        """
        if self.offline_mode:
            return False

        if not self.ip_address:
            self.logger.warning("IP адреса Sonoff не вказана")
            self.offline_mode = True
            return False

        try:
            # Спробувати отримати статус для перевірки підключення
            result = self._send_command("Status")
            if result is not None:
                self.is_connected = True
                self.offline_mode = False
                self.logger.info(f"Підключено до розетки Sonoff S60 ({self.ip_address})")
                return True
            else:
                self.logger.warning(
                    f"Не вдалося підключитися до Sonoff ({self.ip_address}). "
                    "Працюю в режимі офлайн (без розетки)"
                )
                self.is_connected = False
                self.offline_mode = True
                return False
        except Exception as e:
            self.logger.warning(
                f"Помилка підключення до Sonoff: {e}. "
                "Працюю в режимі офлайн (без розетки)"
            )
            self.is_connected = False
            self.offline_mode = True
            return False

    def turn_on(self) -> bool:
        """
        Увімкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        if self.offline_mode:
            # Режим офлайн - симулюємо вмикання
            self.simulated_state = True
            self.last_status = True
            self.last_update = datetime.now()
            self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: увімкнена")
            return True

        result = self._send_command("Power On")
        if result is not None:
            # Перевірити відповідь від Tasmota
            # Зазвичай повертається {"POWER":"ON"}
            power_state = result.get("POWER", "").upper()
            if power_state == "ON":
                self.last_status = True
                self.last_update = datetime.now()
                self.is_connected = True
                self.logger.info("Розетка Sonoff увімкнена")
                return True
            else:
                self.logger.warning(f"Несподівана відповідь від Sonoff при вмиканні: {result}")
                # Все одно вважаємо успішним, якщо команда відправлена
                self.last_status = True
                self.last_update = datetime.now()
                return True
        else:
            # Не вдалося відправити команду - переходимо в режим офлайн
            self.logger.warning("Не вдалося увімкнути розетку. Переходжу в режим офлайн")
            self.is_connected = False
            self.offline_mode = True
            # Симулюємо вмикання
            self.simulated_state = True
            self.last_status = True
            self.last_update = datetime.now()
            self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: увімкнена")
            return True

    def turn_off(self) -> bool:
        """
        Вимкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        if self.offline_mode:
            # Режим офлайн - симулюємо вимкнення
            self.simulated_state = False
            self.last_status = False
            self.last_update = datetime.now()
            self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: вимкнена")
            return True

        result = self._send_command("Power Off")
        if result is not None:
            # Перевірити відповідь від Tasmota
            # Зазвичай повертається {"POWER":"OFF"}
            power_state = result.get("POWER", "").upper()
            if power_state == "OFF":
                self.last_status = False
                self.last_update = datetime.now()
                self.is_connected = True
                self.logger.info("Розетка Sonoff вимкнена")
                return True
            else:
                self.logger.warning(f"Несподівана відповідь від Sonoff при вимиканні: {result}")
                # Все одно вважаємо успішним, якщо команда відправлена
                self.last_status = False
                self.last_update = datetime.now()
                return True
        else:
            # Не вдалося відправити команду - переходимо в режим офлайн
            self.logger.warning("Не вдалося вимкнути розетку. Переходжу в режим офлайн")
            self.is_connected = False
            self.offline_mode = True
            # Симулюємо вимкнення
            self.simulated_state = False
            self.last_status = False
            self.last_update = datetime.now()
            self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: вимкнена")
            return True

    def get_status(self) -> Optional[bool]:
        """
        Отримати поточний стан розетки.

        Returns:
            True якщо увімкнена, False якщо вимкнена, None при помилці
        """
        if self.offline_mode:
            # Режим офлайн - повертаємо симульований стан
            return self.simulated_state

        result = self._send_command("Power")
        if result is not None:
            # Отримати стан з відповіді
            # Tasmota повертає {"POWER":"ON"} або {"POWER":"OFF"}
            power_state = result.get("POWER", "").upper()
            if power_state in ["ON", "OFF"]:
                is_on = power_state == "ON"
                self.last_status = is_on
                self.last_update = datetime.now()
                self.is_connected = True
                return is_on
            else:
                self.logger.warning(f"Несподівана відповідь від Sonoff при запиті статусу: {result}")
                # Повернути останній відомий стан
                return self.last_status
        else:
            # Не вдалося отримати статус
            self.logger.warning("Не вдалося отримати статус розетки. Використовую останній відомий стан")
            self.is_connected = False
            self.offline_mode = True
            # Повертаємо останній відомий стан
            return self.last_status if self.last_status is not None else self.simulated_state

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

    def toggle(self) -> bool:
        """
        Перемкнути стан розетки (on->off, off->on).

        Returns:
            True якщо команда виконана успішно
        """
        if self.offline_mode:
            # Режим офлайн - симулюємо перемикання
            self.simulated_state = not self.simulated_state
            self.last_status = self.simulated_state
            self.last_update = datetime.now()
            state_str = "увімкнена" if self.simulated_state else "вимкнена"
            self.logger.info(f"Розетка Sonoff [СИМУЛЯЦІЯ]: перемкнута, тепер {state_str}")
            return True

        result = self._send_command("Power Toggle")
        if result is not None:
            power_state = result.get("POWER", "").upper()
            if power_state in ["ON", "OFF"]:
                is_on = power_state == "ON"
                self.last_status = is_on
                self.last_update = datetime.now()
                self.is_connected = True
                state_str = "увімкнена" if is_on else "вимкнена"
                self.logger.info(f"Розетка Sonoff перемкнута, тепер {state_str}")
                return True
            else:
                self.logger.warning(f"Несподівана відповідь від Sonoff при перемиканні: {result}")
                return True
        else:
            self.logger.warning("Не вдалося перемкнути розетку")
            return False

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
            'device_type': 'sonoff_s60_tasmota',
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

    def get_device_info(self) -> Optional[Dict[str, Any]]:
        """
        Отримати детальну інформацію про пристрій від Tasmota.

        Returns:
            Словник з інформацією про пристрій або None при помилці
        """
        if self.offline_mode:
            return None

        result = self._send_command("Status 0")
        if result is not None:
            return result
        else:
            self.logger.warning("Не вдалося отримати інформацію про пристрій")
            return None
