"""
SIYI MK15 Transmitter Integration Module.
Handles communication with SIYI MK15 video transmitter.
"""

import serial
import struct
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from enum import IntEnum

logger = logging.getLogger(__name__)


class SIYICommand(IntEnum):
    """SIYI MK15 command codes."""
    HEARTBEAT = 0x0001
    ACK = 0x0002
    GENERAL_REQUEST = 0x0010
    GENERAL_RESPONSE = 0x0011
    VIDEO_TRANSMISSION_START = 0x0020
    VIDEO_TRANSMISSION_STOP = 0x0021
    VIDEO_QUALITY_SET = 0x0022
    TELEMETRY_REQUEST = 0x0030
    TELEMETRY_RESPONSE = 0x0031


class SIYIMK15:
    """SIYI MK15 transmitter interface."""
    
    def __init__(self, serial_port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        """
        Initialize SIYI MK15 connection.
        
        Args:
            serial_port: Serial port path
            baudrate: Baud rate for serial communication
        """
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.running = False
        self.heartbeat_thread = None
        self.response_callbacks: Dict[int, Callable] = {}
        self.telemetry_callbacks = []
        self.last_telemetry: Dict[str, Any] = {}
        
    def connect(self) -> bool:
        """Connect to SIYI MK15 transmitter."""
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1.0,
                bytesize=8,
                parity='N',
                stopbits=1
            )
            
            if not self.ser.is_open:
                logger.error(f"Failed to open serial port {self.serial_port}")
                return False
            
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()
            
            # Start response listener
            listener_thread = threading.Thread(target=self._response_listener, daemon=True)
            listener_thread.start()
            
            logger.info(f"Connected to SIYI MK15 on {self.serial_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to SIYI MK15: {e}")
            return False
    
    def _build_packet(self, command: int, data: bytes = b'') -> bytes:
        """Build SIYI protocol packet."""
        # SIYI protocol: [Header(2)] [Length(2)] [Command(2)] [Data] [Checksum(2)]
        header = 0x55AA
        length = len(data) + 2  # Command + Data
        checksum = 0
        
        packet = struct.pack('>HHH', header, length, command)
        packet += data
        
        # Calculate checksum (simple sum)
        for byte in packet[2:]:  # Skip header
            checksum += byte
        checksum = checksum & 0xFFFF
        
        packet += struct.pack('>H', checksum)
        return packet
    
    def _parse_packet(self, data: bytes) -> Optional[tuple]:
        """Parse SIYI protocol packet."""
        if len(data) < 8:  # Minimum packet size
            return None
        
        header, length, command = struct.unpack('>HHH', data[:6])
        if header != 0x55AA:
            return None
        
        data_payload = data[6:-2]  # Exclude checksum
        received_checksum = struct.unpack('>H', data[-2:])[0]
        
        # Verify checksum
        calculated_checksum = sum(data[2:-2]) & 0xFFFF
        if calculated_checksum != received_checksum:
            logger.warning("Checksum mismatch in SIYI packet")
            return None
        
        return (command, data_payload)
    
    def send_command(self, command: SIYICommand, data: bytes = b'', 
                    callback: Optional[Callable] = None) -> bool:
        """Send command to SIYI MK15."""
        if not self.ser or not self.ser.is_open:
            logger.error("SIYI MK15 not connected")
            return False
        
        try:
            packet = self._build_packet(command.value, data)
            self.ser.write(packet)
            
            if callback:
                self.response_callbacks[command.value] = callback
            
            return True
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def _response_listener(self):
        """Listen for responses from SIYI MK15."""
        buffer = b''
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    buffer += self.ser.read(self.ser.in_waiting)
                    
                    # Try to parse packets
                    while len(buffer) >= 8:
                        packet = self._parse_packet(buffer)
                        if packet:
                            command, data = packet
                            self._handle_response(command, data)
                            # Remove processed packet
                            buffer = buffer[8 + len(data):]
                        else:
                            # Try to find header
                            header_pos = buffer.find(b'\x55\xAA', 1)
                            if header_pos > 0:
                                buffer = buffer[header_pos:]
                            else:
                                break
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error in response listener: {e}")
                time.sleep(0.1)
    
    def _handle_response(self, command: int, data: bytes):
        """Handle response from SIYI MK15."""
        if command == SIYICommand.TELEMETRY_RESPONSE.value:
            self._parse_telemetry(data)
        
        # Call registered callback
        if command in self.response_callbacks:
            try:
                self.response_callbacks[command](data)
            except Exception as e:
                logger.error(f"Error in response callback: {e}")
            finally:
                del self.response_callbacks[command]
    
    def _parse_telemetry(self, data: bytes):
        """Parse telemetry data from SIYI MK15."""
        try:
            # Parse telemetry (adjust based on actual SIYI protocol)
            # This is a placeholder - adjust based on actual SIYI MK15 telemetry format
            if len(data) >= 20:
                # Example parsing (adjust based on actual protocol)
                telemetry = {
                    'timestamp': time.time(),
                    'gps_lat': struct.unpack('>f', data[0:4])[0] if len(data) >= 4 else 0.0,
                    'gps_lon': struct.unpack('>f', data[4:8])[0] if len(data) >= 8 else 0.0,
                    'altitude': struct.unpack('>f', data[8:12])[0] if len(data) >= 12 else 0.0,
                    'roll': struct.unpack('>h', data[12:14])[0] / 100.0 if len(data) >= 14 else 0.0,
                    'pitch': struct.unpack('>h', data[14:16])[0] / 100.0 if len(data) >= 16 else 0.0,
                    'yaw': struct.unpack('>h', data[16:18])[0] / 100.0 if len(data) >= 18 else 0.0,
                }
                
                self.last_telemetry = telemetry
                
                # Notify callbacks
                for callback in self.telemetry_callbacks:
                    try:
                        callback(telemetry)
                    except Exception as e:
                        logger.error(f"Error in telemetry callback: {e}")
        except Exception as e:
            logger.error(f"Error parsing telemetry: {e}")
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat to SIYI MK15."""
        while self.running:
            try:
                self.send_command(SIYICommand.HEARTBEAT)
                time.sleep(1.0)  # Send heartbeat every second
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                time.sleep(1.0)
    
    def start_video_transmission(self, quality: str = "high") -> bool:
        """Start video transmission."""
        quality_map = {"high": 0x01, "medium": 0x02, "low": 0x03}
        quality_code = quality_map.get(quality, 0x01)
        data = struct.pack('B', quality_code)
        return self.send_command(SIYICommand.VIDEO_TRANSMISSION_START, data)
    
    def stop_video_transmission(self) -> bool:
        """Stop video transmission."""
        return self.send_command(SIYICommand.VIDEO_TRANSMISSION_STOP)
    
    def request_telemetry(self) -> bool:
        """Request telemetry data."""
        return self.send_command(SIYICommand.TELEMETRY_REQUEST)
    
    def register_telemetry_callback(self, callback: Callable[[Dict], None]):
        """Register callback for telemetry updates."""
        self.telemetry_callbacks.append(callback)
    
    def get_last_telemetry(self) -> Dict[str, Any]:
        """Get last received telemetry data."""
        return self.last_telemetry.copy()
    
    def disconnect(self):
        """Disconnect from SIYI MK15."""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        logger.info("Disconnected from SIYI MK15")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
