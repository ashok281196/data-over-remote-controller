"""
Telemetry Module
Collects system telemetry data from Jetson device including CPU, GPU, memory, temperature, and network stats.
"""

import psutil
import time
import logging
import threading
from typing import Dict, Optional, Callable
import subprocess
import re

logger = logging.getLogger(__name__)


class JetsonTelemetry:
    """
    Telemetry collector for Jetson devices.
    Collects CPU, GPU, memory, temperature, and network statistics.
    """
    
    def __init__(self, config: dict):
        """
        Initialize telemetry collector.
        
        Args:
            config: Telemetry configuration dictionary
        """
        self.config = config
        self.rate_hz = config.get('rate_hz', 5)
        self.metrics = config.get('metrics', [
            'cpu_usage', 'memory_usage', 'gpu_usage',
            'temperature', 'network_stats', 'camera_fps'
        ])
        
        # State
        self.running = False
        self.telemetry_thread = None
        self.current_data = {}
        self.callbacks = []
        
        # Custom metrics
        self.camera_fps = 0.0
        self.stream_fps = 0.0
        
        logger.info(f"Telemetry collector initialized (rate: {self.rate_hz} Hz)")
    
    def _get_cpu_usage(self) -> Dict:
        """Get CPU usage statistics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
            avg_cpu = sum(cpu_percent) / len(cpu_percent)
            
            return {
                'cpu_usage_percent': round(avg_cpu, 2),
                'cpu_per_core': [round(x, 2) for x in cpu_percent],
                'cpu_count': len(cpu_percent)
            }
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return {}
    
    def _get_memory_usage(self) -> Dict:
        """Get memory usage statistics."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'memory_total_mb': round(mem.total / (1024 * 1024), 2),
                'memory_used_mb': round(mem.used / (1024 * 1024), 2),
                'memory_percent': round(mem.percent, 2),
                'swap_total_mb': round(swap.total / (1024 * 1024), 2),
                'swap_used_mb': round(swap.used / (1024 * 1024), 2),
                'swap_percent': round(swap.percent, 2)
            }
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {}
    
    def _get_gpu_usage(self) -> Dict:
        """Get GPU usage statistics (Jetson-specific)."""
        try:
            # Try to read from tegrastats or similar Jetson-specific tools
            # For now, use a simple approach
            
            # Check if jetson-stats is available
            try:
                result = subprocess.run(
                    ['tegrastats', '--interval', '100', '--stop'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                
                # Parse tegrastats output
                # Format varies, this is a basic parser
                output = result.stdout
                
                gpu_match = re.search(r'GR3D_FREQ (\d+)%', output)
                gpu_percent = int(gpu_match.group(1)) if gpu_match else 0
                
                return {
                    'gpu_usage_percent': gpu_percent,
                    'gpu_available': True
                }
                
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # tegrastats not available, try alternative methods
                return {
                    'gpu_usage_percent': 0,
                    'gpu_available': False,
                    'note': 'GPU monitoring not available'
                }
                
        except Exception as e:
            logger.error(f"Error getting GPU usage: {e}")
            return {}
    
    def _get_temperature(self) -> Dict:
        """Get temperature readings (Jetson-specific)."""
        try:
            temps = {}
            
            # Try to read thermal zones
            try:
                thermal_zones = psutil.sensors_temperatures()
                
                for zone_name, readings in thermal_zones.items():
                    for reading in readings:
                        key = f"{zone_name}_{reading.label}" if reading.label else zone_name
                        temps[key] = round(reading.current, 2)
                        
            except AttributeError:
                # sensors_temperatures not available, try manual reading
                import os
                thermal_path = '/sys/class/thermal'
                
                if os.path.exists(thermal_path):
                    for i in range(10):  # Check first 10 thermal zones
                        temp_file = f'{thermal_path}/thermal_zone{i}/temp'
                        type_file = f'{thermal_path}/thermal_zone{i}/type'
                        
                        if os.path.exists(temp_file):
                            with open(temp_file, 'r') as f:
                                temp = float(f.read().strip()) / 1000.0  # Convert millidegrees to degrees
                            
                            zone_type = f'zone{i}'
                            if os.path.exists(type_file):
                                with open(type_file, 'r') as f:
                                    zone_type = f.read().strip()
                            
                            temps[zone_type] = round(temp, 2)
            
            return temps if temps else {'cpu_thermal': 0.0}
            
        except Exception as e:
            logger.error(f"Error getting temperature: {e}")
            return {}
    
    def _get_network_stats(self) -> Dict:
        """Get network statistics."""
        try:
            net_io = psutil.net_io_counters()
            
            return {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024 * 1024), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024 * 1024), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errors_in': net_io.errin,
                'errors_out': net_io.errout
            }
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return {}
    
    def _collect_telemetry(self) -> Dict:
        """Collect all enabled telemetry metrics."""
        data = {
            'timestamp': time.time(),
            'device': 'jetson'
        }
        
        # Collect enabled metrics
        if 'cpu_usage' in self.metrics:
            data.update(self._get_cpu_usage())
        
        if 'memory_usage' in self.metrics:
            data.update(self._get_memory_usage())
        
        if 'gpu_usage' in self.metrics:
            data.update(self._get_gpu_usage())
        
        if 'temperature' in self.metrics:
            temps = self._get_temperature()
            data['temperatures'] = temps
        
        if 'network_stats' in self.metrics:
            data.update(self._get_network_stats())
        
        if 'camera_fps' in self.metrics:
            data['camera_fps'] = round(self.camera_fps, 2)
            data['stream_fps'] = round(self.stream_fps, 2)
        
        return data
    
    def _telemetry_loop(self):
        """Background telemetry collection loop."""
        logger.info("Starting telemetry collection loop")
        interval = 1.0 / self.rate_hz
        
        while self.running:
            try:
                start_time = time.time()
                
                # Collect telemetry
                telemetry_data = self._collect_telemetry()
                self.current_data = telemetry_data
                
                # Call registered callbacks
                for callback in self.callbacks:
                    try:
                        callback(telemetry_data)
                    except Exception as e:
                        logger.error(f"Error in telemetry callback: {e}")
                
                # Sleep for remaining time
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                time.sleep(interval)
        
        logger.info("Telemetry collection loop stopped")
    
    def register_callback(self, callback: Callable[[Dict], None]):
        """
        Register a callback to be called with telemetry data.
        
        Args:
            callback: Function that accepts telemetry dictionary
        """
        self.callbacks.append(callback)
        logger.info(f"Registered telemetry callback: {callback.__name__}")
    
    def update_camera_fps(self, fps: float):
        """Update camera FPS metric."""
        self.camera_fps = fps
    
    def update_stream_fps(self, fps: float):
        """Update stream FPS metric."""
        self.stream_fps = fps
    
    def get_current_data(self) -> Dict:
        """Get the most recent telemetry data."""
        return self.current_data.copy()
    
    def start(self):
        """Start telemetry collection."""
        if self.running:
            logger.warning("Telemetry already running")
            return
        
        self.running = True
        self.telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self.telemetry_thread.start()
        logger.info("Telemetry collection started")
    
    def stop(self):
        """Stop telemetry collection."""
        logger.info("Stopping telemetry collection")
        self.running = False
        
        if self.telemetry_thread:
            self.telemetry_thread.join(timeout=2.0)
        
        logger.info("Telemetry collection stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test configuration
    test_config = {
        'rate_hz': 2,
        'metrics': [
            'cpu_usage', 'memory_usage', 'gpu_usage',
            'temperature', 'network_stats', 'camera_fps'
        ]
    }
    
    # Test telemetry collection
    def print_telemetry(data: Dict):
        """Print telemetry callback."""
        print("\n=== Telemetry Data ===")
        for key, value in data.items():
            if key != 'temperatures':
                print(f"{key}: {value}")
        
        if 'temperatures' in data:
            print("Temperatures:")
            for zone, temp in data['temperatures'].items():
                print(f"  {zone}: {temp}°C")
    
    with JetsonTelemetry(test_config) as telemetry:
        telemetry.register_callback(print_telemetry)
        
        # Update some metrics manually
        telemetry.update_camera_fps(29.8)
        telemetry.update_stream_fps(28.5)
        
        # Run for 10 seconds
        time.sleep(10)
    
    logger.info("Test completed")
