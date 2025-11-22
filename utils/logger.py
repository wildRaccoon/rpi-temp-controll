"""
Модуль для логування подій програми.
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional


class Logger:
    """Клас для налаштування та використання логування."""
    
    _instance: Optional['Logger'] = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern для Logger."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Ініціалізація Logger (виконується тільки один раз)."""
        if not Logger._initialized:
            self.logger: Optional[logging.Logger] = None
            Logger._initialized = True
    
    def setup(
        self,
        log_file: str = "logs/temperature.log",
        log_level: int = logging.INFO,
        enable_console: bool = True
    ) -> None:
        """
        Налаштувати логування.
        
        Args:
            log_file: Шлях до файлу логів
            log_level: Рівень логування
            enable_console: Чи виводити логи в консоль
        """
        # Створити директорію для логів, якщо не існує
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Налаштувати формат логів
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        # Створити logger
        self.logger = logging.getLogger('temperature_control')
        self.logger.setLevel(log_level)
        
        # Очистити існуючі обробники
        self.logger.handlers.clear()
        
        # Обробник для файлу
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Обробник для консолі
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_formatter = logging.Formatter(log_format, date_format)
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """
        Отримати об'єкт logger.
        
        Returns:
            Logger об'єкт
        """
        if self.logger is None:
            # Якщо logger не налаштований, створити базовий
            self.setup()
        return self.logger
    
    def info(self, message: str) -> None:
        """Записати інформаційне повідомлення."""
        self.get_logger().info(message)
    
    def warning(self, message: str) -> None:
        """Записати попередження."""
        self.get_logger().warning(message)
    
    def error(self, message: str) -> None:
        """Записати помилку."""
        self.get_logger().error(message)
    
    def debug(self, message: str) -> None:
        """Записати debug повідомлення."""
        self.get_logger().debug(message)
    
    def critical(self, message: str) -> None:
        """Записати критичну помилку."""
        self.get_logger().critical(message)


# Глобальна функція для зручності
def get_logger() -> logging.Logger:
    """Отримати глобальний logger."""
    return Logger().get_logger()

