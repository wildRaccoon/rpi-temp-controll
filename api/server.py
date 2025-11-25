"""
REST API сервер для моніторингу системи контролю температури.
"""

from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from typing import Optional
import threading

from sensors.sensor_manager import SensorManager
from controllers.temperature_controller import TemperatureController
from database.db import Database
from utils.config_manager import ConfigManager
from utils.logger import get_logger


class APIServer:
    """Клас для REST API сервера."""
    
    def __init__(
        self,
        sensor_manager: SensorManager,
        temperature_controller: TemperatureController,
        database: Database,
        config: ConfigManager
    ):
        """
        Ініціалізація API сервера.
        
        Args:
            sensor_manager: Менеджер датчиків
            temperature_controller: Контролер температури
            database: База даних
            config: Конфігурація
        """
        self.sensor_manager = sensor_manager
        self.temperature_controller = temperature_controller
        self.database = database
        self.config = config
        self.logger = get_logger()
        
        # Налаштування Flask
        api_config = config.get_section('api')
        self.host = api_config.get('host', '0.0.0.0')
        self.port = api_config.get('port', 8080)
        self.debug = api_config.get('debug', False)
        
        # Створити Flask додаток
        self.app = Flask(__name__, 
                        template_folder='../web/templates',
                        static_folder='../web/static')
        CORS(self.app)
        
        # Зареєструвати маршрути
        self._register_routes()
        
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
    
    def _register_routes(self) -> None:
        """Зареєструвати всі маршрути API."""
        
        # Статичні сторінки
        @self.app.route('/')
        @self.app.route('/status.html')
        def status_page():
            """Сторінка поточного стану."""
            return render_template('status.html', test_mode=self.config.is_test_mode())
        
        @self.app.route('/charts.html')
        def charts_page():
            """Сторінка з графіками."""
            return render_template('charts.html', test_mode=self.config.is_test_mode())
        
        # API ендпоінти
        @self.app.route('/api/status')
        def api_status():
            """Загальний статус системи."""
            sensors = self.sensor_manager.get_all_status()

            # Отримати інформацію про розетку (якщо контролер доступний)
            if self.temperature_controller.sonoff_controller is not None:
                outlet_info = self.temperature_controller.sonoff_controller.get_info()
                outlet_status = 'on' if outlet_info.get('status') else 'off'
            else:
                outlet_status = 'unavailable'

            return jsonify({
                'status': 'running',
                'timestamp': self.temperature_controller.get_system_state()['timestamp'],
                'sensors_count': len(sensors),
                'outlet_status': outlet_status,
                'test_mode': self.config.is_test_mode()
            })
        
        @self.app.route('/api/sensors')
        def api_sensors():
            """Статуси всіх датчиків."""
            sensors = self.sensor_manager.get_all_status()
            return jsonify({'sensors': sensors})
        
        @self.app.route('/api/sensor/<sensor_id>')
        def api_sensor(sensor_id: str):
            """Статус конкретного датчика."""
            sensor = self.sensor_manager.get_sensor(sensor_id)
            if sensor:
                return jsonify(sensor.get_status())
            return jsonify({'error': 'Sensor not found'}), 404
        
        @self.app.route('/api/outlet')
        def api_outlet():
            """Статус розетки Sonoff S60."""
            system_state = self.temperature_controller.get_system_state()

            # Якщо контролер розетки відсутній
            if self.temperature_controller.sonoff_controller is None:
                return jsonify({
                    'status': 'unavailable',
                    'connected': False,
                    'reason': 'Конфігурація Sonoff відсутня',
                    'message': 'Система працює без керування розеткою'
                })

            outlet_info = self.temperature_controller.sonoff_controller.get_info()

            return jsonify({
                'status': 'on' if outlet_info.get('status') else 'off',
                'ip_address': outlet_info.get('ip_address'),
                'last_update': outlet_info.get('last_update'),
                'connected': outlet_info.get('connected', False),
                'reason': system_state.get('outlet_reason'),
                'test_mode': outlet_info.get('test_mode', False)
            })
        
        @self.app.route('/api/system')
        def api_system():
            """Статус системи опалення."""
            system_state = self.temperature_controller.get_system_state()

            # Додати температуру CPU Raspberry Pi
            cpu_temp = self._get_cpu_temperature()
            if cpu_temp is not None:
                system_state['cpu_temp'] = cpu_temp

            return jsonify(system_state)
        
        @self.app.route('/api/history/temperatures')
        def api_history_temperatures():
            """Історичні дані температур."""
            from flask import request

            sensor_id = request.args.get('sensor_id', None)
            hours = int(request.args.get('hours', 3))

            data = self.database.get_temperature_history(sensor_id=sensor_id, hours=hours)

            # Додати назви датчиків для зручного відображення
            sensor_names = {}
            for sid, sensor in self.sensor_manager.sensors.items():
                sensor_names[sid] = sensor.name

            return jsonify({
                'sensor_id': sensor_id,
                'period_hours': hours,
                'data': data,
                'sensor_names': sensor_names
            })
        
        @self.app.route('/api/history/events')
        def api_history_events():
            """Історичні події вмикання/вимикання розетки."""
            from flask import request
            
            hours = int(request.args.get('hours', 3))
            
            events = self.database.get_outlet_events_history(hours=hours)
            
            return jsonify({
                'period_hours': hours,
                'events': events
            })

    def _get_cpu_temperature(self) -> Optional[float]:
        """
        Отримати температуру CPU Raspberry Pi.

        Returns:
            Температура в градусах Цельсія або None
        """
        try:
            # Для Linux систем (Raspberry Pi)
            import platform
            if platform.system() == 'Linux':
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = f.read().strip()
                    return float(temp_raw) / 1000.0
            else:
                # Для інших систем (Windows, macOS) - симуляція
                return None
        except Exception as e:
            self.logger.debug(f"Не вдалося отримати температуру CPU: {e}")
            return None

    def start(self) -> None:
        """Запустити API сервер в окремому потоці."""
        if self.is_running:
            self.logger.warning("API сервер вже запущений")
            return
        
        def run_server():
            self.logger.info(f"Запуск API сервера на {self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=self.debug, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.is_running = True
        self.logger.info("API сервер запущено")
    
    def stop(self) -> None:
        """Зупинити API сервер."""
        # Flask не має прямого способу зупинки, тому просто позначаємо як зупинений
        self.is_running = False
        self.logger.info("API сервер зупинено")

