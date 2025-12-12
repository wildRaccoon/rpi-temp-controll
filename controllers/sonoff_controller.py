"""
Модуль для керування розумною розеткою Sonoff S60 з прошивкою Tasmota.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import requests
from urllib.parse import quote
import time

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

        sonoff_config = config.get_section('sonoff')
        self.ip_address = sonoff_config.get('ip_address')

        # Налаштування повторних спроб
        self.retry_attempts = max(1, min(10, sonoff_config.get('retry_attempts', 3)))
        self.retry_delay = max(0.5, min(10.0, sonoff_config.get('retry_delay', 2.0)))
        self.timeout = max(1.0, min(30.0, sonoff_config.get('connection_timeout', 5.0)))

        # Дозволити автоматичне перемикання в режим симуляції при помилках
        self.allow_simulation = sonoff_config.get('allow_simulation', False)

        # Опціональна підтримка MQTT (поки не реалізована)
        mqtt_config = config.get_section('mqtt')
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
        Відправити команду до Tasmota через HTTP API з повторними спробами.

        Args:
            command: Команда для виконання

        Returns:
            JSON відповідь від Tasmota або None при помилці
        """
        if self.offline_mode:
            return None

        url = self._build_url(command)
        last_error = None

        # Спроби виконати команду з повторами
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()

                # Успішна відповідь - скидаємо offline_mode якщо був активний
                if self.offline_mode and self.allow_simulation:
                    self.logger.info("З'єднання з Sonoff відновлено, вихід з режиму симуляції")
                    self.offline_mode = False

                return response.json()

            except requests.exceptions.Timeout as e:
                last_error = f"Таймаут при спробі зв'язатися з Sonoff ({self.ip_address})"
                if attempt < self.retry_attempts:
                    self.logger.debug(f"{last_error}. Спроба {attempt}/{self.retry_attempts}, повтор через {self.retry_delay}с...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.warning(f"{last_error}. Всі {self.retry_attempts} спроб вичерпано")

            except requests.exceptions.ConnectionError as e:
                last_error = f"Помилка з'єднання з Sonoff ({self.ip_address})"
                if attempt < self.retry_attempts:
                    self.logger.debug(f"{last_error}. Спроба {attempt}/{self.retry_attempts}, повтор через {self.retry_delay}с...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.warning(f"{last_error}. Всі {self.retry_attempts} спроб вичерпано")

            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP помилка від Sonoff: {e}"
                # HTTP помилки зазвичай не потребують повтору
                self.logger.warning(last_error)
                break

            except Exception as e:
                last_error = f"Несподівана помилка при відправці команди до Sonoff: {e}"
                self.logger.error(last_error)
                break

        # Всі спроби вичерпані
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
            if self.allow_simulation:
                # Режим офлайн з дозволом симуляції
                self.simulated_state = True
                self.last_status = True
                self.last_update = datetime.now()
                self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: увімкнена")
                return True
            else:
                # Режим офлайн БЕЗ дозволу симуляції - повертаємо помилку
                self.logger.error("Не вдалося увімкнути розетку: немає зв'язку з пристроєм (симуляція вимкнена)")
                return False

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
            # Не вдалося відправити команду після всіх спроб
            self.is_connected = False

            if self.allow_simulation:
                # Переходимо в режим офлайн
                self.logger.warning("Не вдалося увімкнути розетку після всіх спроб. Переходжу в режим симуляції")
                self.offline_mode = True
                self.simulated_state = True
                self.last_status = True
                self.last_update = datetime.now()
                self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: увімкнена")
                return True
            else:
                # Симуляція вимкнена - повертаємо помилку
                self.logger.error("Не вдалося увімкнути розетку після всіх спроб (симуляція вимкнена)")
                return False

    def turn_off(self) -> bool:
        """
        Вимкнути розетку.

        Returns:
            True якщо команда виконана успішно
        """
        if self.offline_mode:
            if self.allow_simulation:
                # Режим офлайн з дозволом симуляції
                self.simulated_state = False
                self.last_status = False
                self.last_update = datetime.now()
                self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: вимкнена")
                return True
            else:
                # Режим офлайн БЕЗ дозволу симуляції - повертаємо помилку
                self.logger.error("Не вдалося вимкнути розетку: немає зв'язку з пристроєм (симуляція вимкнена)")
                return False

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
            # Не вдалося відправити команду після всіх спроб
            self.is_connected = False

            if self.allow_simulation:
                # Переходимо в режим офлайн
                self.logger.warning("Не вдалося вимкнути розетку після всіх спроб. Переходжу в режим симуляції")
                self.offline_mode = True
                self.simulated_state = False
                self.last_status = False
                self.last_update = datetime.now()
                self.logger.info("Розетка Sonoff [СИМУЛЯЦІЯ]: вимкнена")
                return True
            else:
                # Симуляція вимкнена - повертаємо помилку
                self.logger.error("Не вдалося вимкнути розетку після всіх спроб (симуляція вимкнена)")
                return False

    def get_status(self) -> Optional[bool]:
        """
        Отримати поточний стан розетки.

        Returns:
            True якщо увімкнена, False якщо вимкнена, None при помилці
        """
        if self.offline_mode:
            if self.allow_simulation:
                # Режим офлайн з дозволом симуляції - повертаємо симульований стан
                return self.simulated_state
            else:
                # Режим офлайн БЕЗ дозволу симуляції - повертаємо None (помилка)
                return None

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
            # Не вдалося отримати статус після всіх спроб
            self.is_connected = False

            if self.allow_simulation:
                # Переходимо в режим офлайн
                self.logger.warning("Не вдалося отримати статус розетки. Використовую останній відомий стан (режим симуляції)")
                self.offline_mode = True
                return self.last_status if self.last_status is not None else self.simulated_state
            else:
                # Симуляція вимкнена - повертаємо None
                self.logger.error("Не вдалося отримати статус розетки після всіх спроб (симуляція вимкнена)")
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

    def toggle(self) -> bool:
        """
        Перемкнути стан розетки (on->off, off->on).

        Returns:
            True якщо команда виконана успішно
        """
        if self.offline_mode:
            if self.allow_simulation:
                # Режим офлайн з дозволом симуляції
                self.simulated_state = not self.simulated_state
                self.last_status = self.simulated_state
                self.last_update = datetime.now()
                state_str = "увімкнена" if self.simulated_state else "вимкнена"
                self.logger.info(f"Розетка Sonoff [СИМУЛЯЦІЯ]: перемкнута, тепер {state_str}")
                return True
            else:
                # Режим офлайн БЕЗ дозволу симуляції
                self.logger.error("Не вдалося перемкнути розетку: немає зв'язку з пристроєм (симуляція вимкнена)")
                return False

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
            # Не вдалося перемкнути після всіх спроб
            self.is_connected = False

            if self.allow_simulation:
                self.logger.warning("Не вдалося перемкнути розетку після всіх спроб. Переходжу в режим симуляції")
                self.offline_mode = True
                self.simulated_state = not self.simulated_state
                self.last_status = self.simulated_state
                self.last_update = datetime.now()
                state_str = "увімкнена" if self.simulated_state else "вимкнена"
                self.logger.info(f"Розетка Sonoff [СИМУЛЯЦІЯ]: перемкнута, тепер {state_str}")
                return True
            else:
                self.logger.error("Не вдалося перемкнути розетку після всіх спроб (симуляція вимкнена)")
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
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'allow_simulation': self.allow_simulation,
            'retry_attempts': self.retry_attempts,
            'retry_delay': self.retry_delay,
            'timeout': self.timeout
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
