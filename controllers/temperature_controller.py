"""
Модуль для контролю температури та керування розеткою.
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

from sensors.sensor_manager import SensorManager
from controllers.tapo_controller import TapoController
from tests.test_tapo import TestTapoController
from utils.config_manager import ConfigManager
from utils.logger import get_logger


class TemperatureController:
    """Клас для контролю температури та керування розеткою."""
    
    def __init__(
        self,
        sensor_manager: SensorManager,
        tapo_controller,
        config: ConfigManager
    ):
        """
        Ініціалізація контролера температури.
        
        Args:
            sensor_manager: Менеджер датчиків
            tapo_controller: Контролер розетки Tapo (TapoController або TestTapoController)
            config: Об'єкт ConfigManager
        """
        self.sensor_manager = sensor_manager
        self.tapo_controller = tapo_controller
        self.config = config
        self.logger = get_logger()
        
        # Налаштування з конфігурації
        control_config = config.get_section('control')
        self.boiler_critical_temp = control_config.get('boiler_critical_temp', 85.0)
        self.accumulator_critical_temp = control_config.get('accumulator_critical_temp', 80.0)
        self.boiler_safe_temp = control_config.get('boiler_safe_temp', 70.0)
        self.accumulator_safe_temp = control_config.get('accumulator_safe_temp', 65.0)
        self.chimney_low_temp = control_config.get('chimney_low_temp', 100.0)
        self.hysteresis = control_config.get('hysteresis', 3.0)
        self.startup_duration = timedelta(seconds=control_config.get('startup_duration', 300))
        
        # Стан системи
        self.start_time = datetime.now()
        self.current_outlet_state: Optional[bool] = None
        self.last_outlet_reason: Optional[str] = None
        self.last_temperatures: Dict[str, Optional[float]] = {}
    
    def is_startup_period(self) -> bool:
        """
        Перевірити, чи триває початковий період (котел щойно затопили).
        
        Returns:
            True якщо триває початковий період
        """
        elapsed = datetime.now() - self.start_time
        return elapsed < self.startup_duration
    
    def get_temperatures(self) -> Dict[str, Optional[float]]:
        """
        Отримати температури з усіх датчиків.
        
        Returns:
            Словник {sensor_id: temperature}
        """
        readings = self.sensor_manager.read_all()
        self.last_temperatures = readings
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
        
        # Отримати поточний стан розетки
        current_state = self.tapo_controller.get_status()
        
        # Визначити, чи потрібно змінити стан
        should_on, reason_on = self.should_turn_on()
        should_off, reason_off = self.should_turn_off()
        
        # Логіка керування
        if should_on and (current_state is False or current_state is None):
            # Потрібно увімкнути
            if self.tapo_controller.turn_on():
                self.current_outlet_state = True
                self.last_outlet_reason = reason_on
                self.logger.info(f"Розетка увімкнена. Причина: {reason_on}")
                return reason_on
        
        elif should_off and (current_state is True):
            # Потрібно вимкнути
            if self.tapo_controller.turn_off():
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
        outlet_status = self.tapo_controller.get_status()
        
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
            'outlet_status': 'on' if outlet_status else 'off',
            'outlet_reason': self.last_outlet_reason,
            'timestamp': datetime.now().isoformat(),
            'startup_remaining_seconds': max(0, int((self.startup_duration - (datetime.now() - self.start_time)).total_seconds()))
        }

