"""
Модуль для контролю температури та керування розеткою.
"""

from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from collections import deque

from sensors.sensor_manager import SensorManager
from controllers.sonoff_controller import SonoffController
from tests.test_sonoff import TestSonoffController
from utils.config_manager import ConfigManager
from utils.logger import get_logger


class TemperatureController:
    """Клас для контролю температури та керування розеткою."""
    
    def __init__(
        self,
        sensor_manager: SensorManager,
        sonoff_controller,
        config: ConfigManager
    ):
        """
        Ініціалізація контролера температури.

        Args:
            sensor_manager: Менеджер датчиків
            sonoff_controller: Контролер розетки Sonoff (SonoffController або TestSonoffController)
            config: Об'єкт ConfigManager
        """
        self.sensor_manager = sensor_manager
        self.sonoff_controller = sonoff_controller
        self.config = config
        self.logger = get_logger()
        
        # Налаштування з конфігурації
        control_config = config.get_section('control')
        self.boiler_critical_temp = control_config.get('boiler_critical_temp', 85.0)
        self.accumulator_critical_temp = control_config.get('accumulator_critical_temp', 80.0)
        self.boiler_safe_temp = control_config.get('boiler_safe_temp', 70.0)
        self.accumulator_safe_temp = control_config.get('accumulator_safe_temp', 65.0)
        self.chimney_critical_temp = control_config.get('chimney_critical_temp', 250.0)
        self.chimney_low_temp = control_config.get('chimney_low_temp', 100.0)
        self.hysteresis = control_config.get('hysteresis', 3.0)

        # Налаштування для визначення режиму startup (затоплення)
        self.startup_detection_period = timedelta(seconds=control_config.get('startup_detection_period', 120))  # 2 хвилини
        self.startup_temp_increase = control_config.get('startup_temp_increase', 5.0)  # Мінімальне збільшення температури (°C)

        # Стан системи
        self.current_outlet_state: Optional[bool] = None
        self.last_outlet_reason: Optional[str] = None
        self.last_temperatures: Dict[str, Optional[float]] = {}

        # Історія температур для визначення тренду (зберігаємо за останні 2 хвилини)
        self.temperature_history: deque = deque(maxlen=100)  # (timestamp, boiler_temp, chimney_temp)
    
    def is_startup_period(self) -> bool:
        """
        Перевірити, чи триває початковий період (котел щойно затопили).
        Визначається за зростанням температури котла і димоходу за останні 2 хвилини.

        Returns:
            True якщо триває початковий період (температури активно зростають)
        """
        # Потрібно мати достатньо даних для аналізу (хоча б 2 точки)
        if len(self.temperature_history) < 2:
            return False

        now = datetime.now()
        # Фільтруємо записи за останній період (startup_detection_period)
        recent_readings = [
            reading for reading in self.temperature_history
            if (now - reading[0]) <= self.startup_detection_period
        ]

        if len(recent_readings) < 2:
            return False

        # Перша і остання точка для порівняння
        first_reading = recent_readings[0]
        last_reading = recent_readings[-1]

        first_boiler = first_reading[1]
        last_boiler = last_reading[1]
        first_chimney = first_reading[2]
        last_chimney = last_reading[2]

        # Перевірка зростання температур
        boiler_increasing = False
        chimney_increasing = False

        if first_boiler is not None and last_boiler is not None:
            boiler_increase = last_boiler - first_boiler
            boiler_increasing = boiler_increase >= self.startup_temp_increase

        if first_chimney is not None and last_chimney is not None:
            chimney_increase = last_chimney - first_chimney
            chimney_increasing = chimney_increase >= self.startup_temp_increase

        # Режим startup активний якщо обидві температури зростають
        is_startup = boiler_increasing and chimney_increasing

        return is_startup
    
    def get_temperatures(self) -> Dict[str, Optional[float]]:
        """
        Отримати температури з усіх датчиків.

        Returns:
            Словник {sensor_id: temperature}
        """
        readings = self.sensor_manager.read_all()
        self.last_temperatures = readings

        # Зберегти в історію для аналізу тренду
        boiler_temp = None
        chimney_temp = None

        for sensor_id, temp in readings.items():
            if 'boiler' in sensor_id:
                boiler_temp = temp
            elif 'chimney' in sensor_id:
                chimney_temp = temp

        # Додати запис до історії (timestamp, boiler_temp, chimney_temp)
        self.temperature_history.append((datetime.now(), boiler_temp, chimney_temp))

        return readings
    
    def get_boiler_temp(self) -> Optional[float]:
        """Отримати температуру котла."""
        # Шукаємо датчик котла
        for sensor_id in self.last_temperatures:
            if 'boiler' in sensor_id:
                return self.last_temperatures[sensor_id]
        return None
    
    def get_accumulator_temps(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Отримати температури термоакумулятора (знизу, зверху).
        
        Returns:
            Кортеж (температура_знизу, температура_зверху)
        """
        bottom_temp = None
        top_temp = None
        
        for sensor_id, temp in self.last_temperatures.items():
            if 'accumulator_bottom' in sensor_id:
                bottom_temp = temp
            elif 'accumulator_top' in sensor_id:
                top_temp = temp
        
        return (bottom_temp, top_temp)
    
    def get_chimney_temp(self) -> Optional[float]:
        """Отримати температуру димаря."""
        for sensor_id in self.last_temperatures:
            if 'chimney' in sensor_id:
                return self.last_temperatures[sensor_id]
        return None
    
    def should_turn_on(self) -> Tuple[bool, str]:
        """
        Визначити, чи потрібно увімкнути розетку.

        Returns:
            Кортеж (чи_увімкнути, причина)
        """
        # Початковий період
        if self.is_startup_period():
            return (True, "startup")

        boiler_temp = self.get_boiler_temp()
        bottom_temp, top_temp = self.get_accumulator_temps()
        max_accumulator_temp = max(
            t for t in [bottom_temp, top_temp] if t is not None
        ) if (bottom_temp is not None or top_temp is not None) else None
        chimney_temp = self.get_chimney_temp()

        # Критична температура димоходу (найвищий пріоритет!)
        if chimney_temp is not None:
            if chimney_temp >= (self.chimney_critical_temp - self.hysteresis):
                return (True, "chimney_critical")

        # Критична температура котла
        if boiler_temp is not None:
            if boiler_temp >= (self.boiler_critical_temp - self.hysteresis):
                return (True, "boiler_critical")

        # Критична температура термоакумулятора
        if max_accumulator_temp is not None:
            if max_accumulator_temp >= (self.accumulator_critical_temp - self.hysteresis):
                return (True, "accumulator_critical")

        return (False, None)
    
    def should_turn_off(self) -> Tuple[bool, str]:
        """
        Визначити, чи потрібно вимкнути розетку.

        Returns:
            Кортеж (чи_вимкнути, причина)
        """
        boiler_temp = self.get_boiler_temp()
        bottom_temp, top_temp = self.get_accumulator_temps()
        max_accumulator_temp = max(
            t for t in [bottom_temp, top_temp] if t is not None
        ) if (bottom_temp is not None or top_temp is not None) else None
        chimney_temp = self.get_chimney_temp()

        # НЕ вимикати насос якщо димохід перегрітий (має пріоритет)
        if chimney_temp is not None:
            if chimney_temp >= (self.chimney_critical_temp - self.hysteresis):
                return (False, None)

        # Перевірка безпечних температур
        boiler_safe = boiler_temp is None or boiler_temp < (self.boiler_safe_temp + self.hysteresis)
        accumulator_safe = max_accumulator_temp is None or max_accumulator_temp < (self.accumulator_safe_temp + self.hysteresis)
        chimney_low = chimney_temp is None or chimney_temp < self.chimney_low_temp

        if boiler_safe and accumulator_safe and chimney_low:
            return (True, "safe_temperatures")

        return (False, None)
    
    def update_control(self) -> Optional[str]:
        """
        Оновити контроль температури та керування розеткою.

        Returns:
            Причина зміни стану або None
        """
        # Отримати поточні температури
        self.get_temperatures()

        # Якщо контролер розетки відсутній, тільки логуємо
        if self.sonoff_controller is None:
            should_on, reason_on = self.should_turn_on()
            should_off, reason_off = self.should_turn_off()
            if should_on:
                self.logger.info(f"[БЕЗ РОЗЕТКИ] Потрібно увімкнути розетку. Причина: {reason_on}")
            elif should_off:
                self.logger.info(f"[БЕЗ РОЗЕТКИ] Потрібно вимкнути розетку. Причина: {reason_off}")
            return None

        # Отримати поточний стан розетки
        current_state = self.sonoff_controller.get_status()

        # Визначити, чи потрібно змінити стан
        should_on, reason_on = self.should_turn_on()
        should_off, reason_off = self.should_turn_off()

        # Логіка керування
        if should_on and (current_state is False or current_state is None):
            # Потрібно увімкнути
            if self.sonoff_controller.turn_on():
                self.current_outlet_state = True
                self.last_outlet_reason = reason_on
                self.logger.info(f"Розетка увімкнена. Причина: {reason_on}")
                return reason_on

        elif should_off and (current_state is True):
            # Потрібно вимкнути
            if self.sonoff_controller.turn_off():
                self.current_outlet_state = False
                self.last_outlet_reason = reason_off
                self.logger.info(f"Розетка вимкнена. Причина: {reason_off}")
                return reason_off

        # Стан не змінився
        return None
    
    def get_system_state(self) -> Dict[str, Any]:
        """
        Отримати поточний стан системи.

        Returns:
            Словник зі станом системи
        """
        boiler_temp = self.get_boiler_temp()
        bottom_temp, top_temp = self.get_accumulator_temps()
        chimney_temp = self.get_chimney_temp()

        # Отримати стан розетки (якщо контролер доступний)
        if self.sonoff_controller is not None:
            outlet_status = self.sonoff_controller.get_status()
        else:
            outlet_status = None

        # Визначити загальний стан системи
        if self.is_startup_period():
            system_state = "startup"
        elif chimney_temp is not None and chimney_temp < self.chimney_low_temp:
            system_state = "cooling_down"
        else:
            system_state = "running"

        return {
            'state': system_state,
            'boiler_temp': boiler_temp,
            'accumulator_bottom_temp': bottom_temp,
            'accumulator_top_temp': top_temp,
            'chimney_temp': chimney_temp,
            'outlet_status': 'on' if outlet_status else ('off' if outlet_status is False else 'unavailable'),
            'outlet_reason': self.last_outlet_reason,
            'timestamp': datetime.now().isoformat(),
            'is_startup': self.is_startup_period(),
            'temperature_history_size': len(self.temperature_history)
        }

