"""
Telemetry data handler for collecting and managing telemetry information.
"""

import time
import logging
import psutil
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class TelemetryData:
    """Telemetry data structure."""
    timestamp: float
    gps_lat: float = 0.0
    gps_lon: float = 0.0
    altitude: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    battery_voltage: float = 0.0
    battery_percentage: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_usage: float = 0.0
    temperature: float = 0.0
    frame_rate: float = 0.0


class TelemetryHandler:
    """Handles telemetry data collection and distribution."""
    
    def __init__(self, update_rate: int = 10, include_gps: bool = True,
                 include_attitude: bool = True, include_battery: bool = True,
                 include_system_stats: bool = True):
        """
        Initialize telemetry handler.
        
        Args:
            update_rate: Update rate in Hz
            include_gps: Include GPS data
            include_attitude: Include attitude data
            include_battery: Include battery data
            include_system_stats: Include system statistics
        """
        self.update_rate = update_rate
        self.include_gps = include_gps
        self.include_attitude = include_attitude
        self.include_battery = include_battery
        self.include_system_stats = include_system_stats
        
        self.running = False
        self.telemetry_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.current_telemetry = TelemetryData(timestamp=time.time())
        self.frame_count = 0
        self.last_frame_time = time.time()
        
    def start(self):
        """Start telemetry collection."""
        self.running = True
        logger.info(f"Telemetry handler started at {self.update_rate} Hz")
    
    def stop(self):
        """Stop telemetry collection."""
        self.running = False
        logger.info("Telemetry handler stopped")
    
    def update_from_siyi(self, siyi_telemetry: Dict[str, Any]):
        """Update telemetry from SIYI MK15 data."""
        if self.include_gps:
            self.current_telemetry.gps_lat = siyi_telemetry.get('gps_lat', 0.0)
            self.current_telemetry.gps_lon = siyi_telemetry.get('gps_lon', 0.0)
            self.current_telemetry.altitude = siyi_telemetry.get('altitude', 0.0)
        
        if self.include_attitude:
            self.current_telemetry.roll = siyi_telemetry.get('roll', 0.0)
            self.current_telemetry.pitch = siyi_telemetry.get('pitch', 0.0)
            self.current_telemetry.yaw = siyi_telemetry.get('yaw', 0.0)
    
    def update_system_stats(self):
        """Update system statistics."""
        if not self.include_system_stats:
            return
        
        try:
            # CPU usage
            self.current_telemetry.cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.current_telemetry.memory_usage = memory.percent
            
            # Temperature (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get first available temperature sensor
                    for name, entries in temps.items():
                        if entries:
                            self.current_telemetry.temperature = entries[0].current
                            break
            except:
                pass
            
            # GPU usage (Jetson specific - requires jetson-stats or nvidia-ml-py)
            try:
                # Try to get GPU usage from jetson-stats if available
                import subprocess
                result = subprocess.run(
                    ['tegrastats', '--interval', '100', '--logfile', '/dev/stdout'],
                    capture_output=True,
                    text=True,
                    timeout=0.2
                )
                # Parse tegrastats output (simplified)
                # In production, use proper parsing or jetson-stats library
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error updating system stats: {e}")
    
    def update_frame_rate(self):
        """Update frame rate calculation."""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        
        if elapsed >= 1.0:  # Calculate FPS every second
            self.current_telemetry.frame_rate = self.frame_count / elapsed
            self.frame_count = 0
            self.last_frame_time = current_time
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data as dictionary."""
        self.current_telemetry.timestamp = time.time()
        self.update_system_stats()
        return asdict(self.current_telemetry)
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for telemetry updates."""
        self.telemetry_callbacks.append(callback)
    
    def notify_callbacks(self, telemetry: Dict[str, Any]):
        """Notify all registered callbacks."""
        for callback in self.telemetry_callbacks:
            try:
                callback(telemetry)
            except Exception as e:
                logger.error(f"Error in telemetry callback: {e}")
    
    def to_json(self) -> str:
        """Convert telemetry to JSON string."""
        return json.dumps(self.get_telemetry())
