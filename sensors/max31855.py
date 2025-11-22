"""
Модуль для роботи з датчиком MAX31855 (SPI термопара).
"""

from typing import Optional, Dict, Any
from datetime import datetime

# Спочатку намагаємось використати spidev (простіше і надійніше на Raspberry Pi)
try:
    import spidev
    import RPi.GPIO as GPIO
    SPIDEV_AVAILABLE = True
except ImportError:
    SPIDEV_AVAILABLE = False

# Adafruit як запасний варіант
try:
    import adafruit_max31855 as max31855
    import board
    import busio
    import digitalio
    ADAFRUIT_AVAILABLE = True
except (ImportError, NameError):
    ADAFRUIT_AVAILABLE = False

from sensors.base import BaseSensor
from utils.logger import get_logger


class MAX31855Sensor(BaseSensor):
    """Клас для роботи з датчиком MAX31855."""
    
    def __init__(self, sensor_id: str, name: str, config: Dict[str, Any]):
        """
        Ініціалізація датчика MAX31855.
        
        Args:
            sensor_id: Унікальний ідентифікатор датчика
            name: Назва датчика
            config: Конфігурація датчика (cs_pin, spi_port, spi_device, enabled, name)
        """
        super().__init__(sensor_id, name, config)
        self.cs_pin = config.get('cs_pin', 8)
        self.spi_port = config.get('spi_port', 0)
        self.spi_device = config.get('spi_device', 0)
        self.sensor = None
        self.logger = get_logger()
        self.use_spidev = False
    
    def initialize(self) -> bool:
        """
        Ініціалізувати датчик MAX31855.

        Returns:
            True якщо ініціалізація успішна
        """
        if not self.enabled:
            self.logger.info(f"MAX31855 {self.name}: вимкнено в конфігурації")
            return False

        # Спочатку спробувати spidev (простіше і надійніше)
        if SPIDEV_AVAILABLE:
            try:
                import spidev
                import RPi.GPIO as GPIO

                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.cs_pin, GPIO.OUT)
                GPIO.output(self.cs_pin, GPIO.HIGH)

                spi = spidev.SpiDev()
                spi.open(self.spi_port, self.spi_device)
                spi.max_speed_hz = 5000000
                spi.mode = 0b11

                self.sensor = {
                    'spi': spi,
                    'cs_pin': self.cs_pin
                }
                self.use_spidev = True
                self.logger.info(f"MAX31855 {self.name}: ініціалізовано (spidev, CS: {self.cs_pin})")
                return True
            except Exception as e:
                self.logger.warning(f"MAX31855 {self.name}: помилка spidev - {e}, спроба adafruit")

        # Якщо spidev не працює, спробувати adafruit бібліотеку
        if ADAFRUIT_AVAILABLE:
            try:
                spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
                cs = digitalio.DigitalInOut(getattr(board, f"D{self.cs_pin}"))
                self.sensor = max31855.MAX31855(spi, cs)
                self.logger.info(f"MAX31855 {self.name}: ініціалізовано (adafruit, CS: {self.cs_pin})")
                return True
            except Exception as e:
                self.logger.error(f"MAX31855 {self.name}: помилка adafruit - {e}")

        self.logger.error(
            f"MAX31855 {self.name}: не вдалося ініціалізувати. "
            f"Встановіть: pip install spidev RPi.GPIO (рекомендовано) або pip install adafruit-circuitpython-max31855"
        )
        return False
    
    def _read_spidev(self) -> Optional[float]:
        """Зчитати температуру через spidev."""
        try:
            import RPi.GPIO as GPIO
            
            spi = self.sensor['spi']
            cs_pin = self.sensor['cs_pin']
            
            # Вимкнути CS
            GPIO.output(cs_pin, GPIO.LOW)
            
            # Прочитати 4 байти
            data = spi.readbytes(4)
            
            # Увімкнути CS
            GPIO.output(cs_pin, GPIO.HIGH)
            
            # Перевірити помилки
            if data[3] & 0x07:
                # Помилка термопари
                return None
            
            # Конвертувати дані в температуру
            temp = ((data[0] << 6) | (data[1] >> 2)) * 0.25
            if data[0] & 0x80:
                temp -= 1024
            
            return temp
            
        except Exception as e:
            self.logger.error(f"MAX31855 {self.name}: помилка spidev зчитування - {e}")
            return None
    
    def read_temperature(self) -> Optional[float]:
        """
        Зчитати температуру з датчика MAX31855.

        Returns:
            Температура в градусах Цельсія або None при помилці
        """
        if not self.enabled or not self.sensor:
            return None

        try:
            if self.use_spidev:
                temperature = self._read_spidev()
            else:
                # adafruit бібліотека
                temperature = self.sensor.temperature

            if temperature is None:
                self.record_error()
                return None

            # Валідація: температура димоходу не повинна перевищувати 300°C
            # Якщо більше - це помилка зчитування
            if temperature > 300.0:
                self.logger.warning(f"MAX31855 {self.name}: температура {temperature:.1f}°C перевищує 300°C - помилка зчитування")
                self.record_error()
                return None

            self.last_reading = temperature
            self.last_update = datetime.now()
            self.reset_errors()
            return temperature

        except Exception as e:
            self.logger.error(f"MAX31855 {self.name}: помилка зчитування - {e}")
            self.record_error()
            return None
    
    def __del__(self):
        """Очистити ресурси при видаленні."""
        if self.use_spidev and self.sensor:
            try:
                self.sensor['spi'].close()
            except:
                pass

