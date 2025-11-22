"""
Модуль для роботи з базою даних SQLite.
"""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from database.models import TemperatureReading, OutletEvent
from utils.logger import get_logger


class Database:
    """Клас для роботи з базою даних SQLite."""
    
    def __init__(self, db_file: str = "data/temperature.db"):
        """
        Ініціалізація бази даних.
        
        Args:
            db_file: Шлях до файлу бази даних
        """
        self.db_file = Path(db_file)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger()
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Отримати з'єднання з базою даних."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_database(self) -> None:
        """Ініціалізувати структуру бази даних."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Таблиця для зчитувань температури
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temperature_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                temperature REAL NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблиця для подій розетки
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outlet_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Індекси для швидкого пошуку
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temperature_timestamp 
            ON temperature_readings(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_temperature_sensor 
            ON temperature_readings(sensor_id, timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_outlet_timestamp 
            ON outlet_events(timestamp)
        """)
        
        conn.commit()
        conn.close()
        self.logger.info(f"База даних ініціалізована: {self.db_file}")
    
    def save_temperature_reading(self, sensor_id: str, temperature: float, timestamp: Optional[datetime] = None) -> bool:
        """
        Зберегти зчитування температури.
        
        Args:
            sensor_id: ID датчика
            temperature: Температура
            timestamp: Час зчитування (за замовчуванням - зараз)
        
        Returns:
            True якщо збереження успішне
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO temperature_readings (sensor_id, temperature, timestamp)
                VALUES (?, ?, ?)
            """, (sensor_id, temperature, timestamp))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Помилка збереження температури: {e}")
            return False
    
    def save_outlet_event(self, action: str, reason: str, timestamp: Optional[datetime] = None) -> bool:
        """
        Зберегти подію вмикання/вимикання розетки.
        
        Args:
            action: 'on' або 'off'
            reason: Причина зміни стану
            timestamp: Час події (за замовчуванням - зараз)
        
        Returns:
            True якщо збереження успішне
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO outlet_events (action, reason, timestamp)
                VALUES (?, ?, ?)
            """, (action, reason, timestamp))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Помилка збереження події розетки: {e}")
            return False
    
    def get_temperature_history(
        self,
        sensor_id: Optional[str] = None,
        hours: int = 3,
        max_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Отримати історичні дані температур.
        
        Args:
            sensor_id: ID датчика (опціонально, якщо None - всі датчики)
            hours: Кількість годин для отримання
            max_hours: Максимальна кількість годин
        
        Returns:
            Список словників з даними
        """
        hours = min(hours, max_hours)
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if sensor_id:
                cursor.execute("""
                    SELECT sensor_id, temperature, timestamp
                    FROM temperature_readings
                    WHERE sensor_id = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (sensor_id, since))
            else:
                cursor.execute("""
                    SELECT sensor_id, temperature, timestamp
                    FROM temperature_readings
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """, (since,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'sensor_id': row['sensor_id'],
                    'temperature': row['temperature'],
                    'timestamp': row['timestamp']
                }
                for row in rows
            ]
        except Exception as e:
            self.logger.error(f"Помилка отримання історії температур: {e}")
            return []
    
    def get_outlet_events_history(self, hours: int = 3, max_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Отримати історичні події розетки.
        
        Args:
            hours: Кількість годин для отримання
            max_hours: Максимальна кількість годин
        
        Returns:
            Список словників з подіями
        """
        hours = min(hours, max_hours)
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT action, reason, timestamp
                FROM outlet_events
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (since,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'action': row['action'],
                    'reason': row['reason'],
                    'timestamp': row['timestamp']
                }
                for row in rows
            ]
        except Exception as e:
            self.logger.error(f"Помилка отримання історії подій: {e}")
            return []
    
    def cleanup_old_data(self, retention_days: int = 7) -> int:
        """
        Видалити старі дані з бази.
        
        Args:
            retention_days: Кількість днів для збереження
        
        Returns:
            Кількість видалених записів
        """
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        deleted_count = 0
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Видалити старі зчитування температур
            cursor.execute("""
                DELETE FROM temperature_readings
                WHERE timestamp < ?
            """, (cutoff_date,))
            deleted_temps = cursor.rowcount
            
            # Видалити старі події розетки
            cursor.execute("""
                DELETE FROM outlet_events
                WHERE timestamp < ?
            """, (cutoff_date,))
            deleted_events = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            deleted_count = deleted_temps + deleted_events
            if deleted_count > 0:
                self.logger.info(f"Видалено {deleted_count} старих записів (старше {retention_days} днів)")
            
            return deleted_count
        except Exception as e:
            self.logger.error(f"Помилка очищення бази даних: {e}")
            return 0

