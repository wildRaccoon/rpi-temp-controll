"""
Модуль для управління конфігурацією програми.
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Клас для завантаження та управління конфігурацією."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Ініціалізація ConfigManager.
        
        Args:
            config_path: Шлях до файлу конфігурації
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Завантажити конфігурацію з файлу."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Файл конфігурації не знайдено: {self.config_path}\n"
                f"Скопіюйте config.example.yaml як config.yaml та налаштуйте його."
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Помилка парсингу YAML: {e}")
        except Exception as e:
            raise RuntimeError(f"Помилка завантаження конфігурації: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Отримати значення з конфігурації за ключем.
        
        Args:
            key: Ключ у форматі 'section.subsection.key' або просто 'key'
            default: Значення за замовчуванням, якщо ключ не знайдено
        
        Returns:
            Значення з конфігурації або default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Отримати всю секцію конфігурації.
        
        Args:
            section: Назва секції
        
        Returns:
            Словник з налаштуваннями секції або порожній словник
        """
        return self.config.get(section, {})
    
    def is_test_mode(self) -> bool:
        """Перевірити, чи увімкнено тестовий режим."""
        test_mode = self.get_section('test_mode')
        return test_mode.get('enabled', False)
    
    def get_test_scenario(self) -> Optional[str]:
        """Отримати тестовий сценарій."""
        test_mode = self.get_section('test_mode')
        return test_mode.get('scenario')
    
    def get_test_temperatures(self) -> Dict[str, float]:
        """Отримати тестові температури."""
        test_mode = self.get_section('test_mode')
        return test_mode.get('test_temperatures', {})
    
    def validate(self) -> bool:
        """
        Валідація конфігурації.
        
        Returns:
            True якщо конфігурація валідна
        """
        required_sections = ['sensors', 'tapo', 'control', 'api']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Відсутня обов'язкова секція: {section}")
        
        # Перевірка налаштувань датчиків
        sensors = self.get_section('sensors')
        if not sensors.get('ds18b20') and not sensors.get('max31855'):
            raise ValueError("Повинен бути увімкнений хоча б один датчик")
        
        # Перевірка налаштувань Tapo
        tapo = self.get_section('tapo')
        if not tapo.get('ip_address'):
            raise ValueError("Не вказано IP адресу розетки Tapo")
        
        return True
    
    def reload(self) -> None:
        """Перезавантажити конфігурацію з файлу."""
        self.load_config()

