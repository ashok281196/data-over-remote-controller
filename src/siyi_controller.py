"""
SIYI MK15 Controller Module
Handles communication with SIYI MK15 handheld ground station for video transmission.
Implements SIYI SDK protocol for gimbal control and video streaming.
"""

import socket
import struct
import threading
import time
import logging
from typing import Optional, Tuple
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class SIYIProtocol:
    """SIYI SDK Protocol implementation."""
    
    # Command IDs
    CMD_ACQUIRE_FW_VERSION = 0x01
    CMD_HARDWARE_ID = 0x02
    CMD_GIMBAL_ATTITUDE = 0x0D
    CMD_GIMBAL_SPEED = 0x07
    CMD_CENTER = 0x08
    CMD_ACQUIRE_GIMBAL_INFO = 0x0A
    CMD_FUNCTION_FEEDBACK = 0x09
    CMD_PHOTO = 0x0C
    CMD_RECORD = 0x0D
    CMD_ZOOM = 0x0F
    
    # Frame structure
    STX1 = 0x66
    STX2 = 0xCC
    
    @staticmethod
    def calc_crc16(data: bytes) -> int:
        """Calculate CRC16 checksum."""
        crc = 0
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    @classmethod
    def build_packet(cls, cmd_id: int, data: bytes = b'') -> bytes:
        """
        Build SIYI protocol packet.
        
        Args:
            cmd_id: Command ID
            data: Command data payload
            
        Returns:
            Complete packet with header, CRC, and data
        """
        data_len = len(data)
        
        # Header: STX1(1) + STX2(1) + CTRL(1) + Data_len(2) + SEQ(2) + CMD_ID(1) + DATA(n)
        ctrl = 0
        seq = 0
        
        header = struct.pack('<BBBHHB',
                           cls.STX1,
                           cls.STX2,
                           ctrl,
                           data_len,
                           seq,
                           cmd_id)
        
        packet = header + data
        
        # Calculate CRC16 (low byte, high byte)
        crc = cls.calc_crc16(packet)
        crc_bytes = struct.pack('<H', crc)
        
        return packet + crc_bytes
    
    @classmethod
    def parse_packet(cls, data: bytes) -> Optional[Tuple[int, bytes]]:
        """
        Parse SIYI protocol packet.
        
        Args:
            data: Raw packet data
            
        Returns:
            Tuple of (cmd_id, payload) or None if invalid
        """
        if len(data) < 10:  # Minimum packet size
            return None
        
        # Verify STX
        if data[0] != cls.STX1 or data[1] != cls.STX2:
            return None
        
        # Extract header
        ctrl = data[2]
        data_len = struct.unpack('<H', data[3:5])[0]
        seq = struct.unpack('<H', data[5:7])[0]
        cmd_id = data[7]
        
        # Verify packet length
        expected_len = 8 + data_len + 2  # header + data + crc
        if len(data) < expected_len:
            return None
        
        payload = data[8:8+data_len]
        
        # Verify CRC
        crc_received = struct.unpack('<H', data[8+data_len:8+data_len+2])[0]
        crc_calculated = cls.calc_crc16(data[:8+data_len])
        
        if crc_received != crc_calculated:
            logger.warning("CRC mismatch")
            return None
        
        return cmd_id, payload


class SIYIMKController:
    """
    SIYI MK15 Ground Station Controller.
    Handles video streaming and telemetry to SIYI MK15.
    """
    
    def __init__(self, config: dict):
        """
        Initialize SIYI controller.
        
        Args:
            config: SIYI configuration dictionary
        """
        self.config = config
        self.transmitter_ip = config.get('transmitter_ip', '192.168.144.25')
        self.video_port = config.get('video_output_port', 5600)
        self.control_port = config.get('control_port', 37260)
        
        # Sockets
        self.video_socket = None
        self.control_socket = None
        
        # State
        self.running = False
        self.connected = False
        
        # Video streaming
        self.video_thread = None
        self.video_queue = None
        
        logger.info(f"SIYI MK15 Controller initialized for {self.transmitter_ip}")
    
    def connect(self) -> bool:
        """
        Connect to SIYI MK15 transmitter.
        
        Returns:
            True if connected successfully
        """
        try:
            # Create video streaming socket (UDP)
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"Video socket created for {self.transmitter_ip}:{self.video_port}")
            
            # Create control socket (UDP)
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.control_socket.bind(('0.0.0.0', self.control_port))
            self.control_socket.settimeout(1.0)
            logger.info(f"Control socket bound to port {self.control_port}")
            
            # Send initial connection packet
            self._send_heartbeat()
            
            self.connected = True
            logger.info("Connected to SIYI MK15")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SIYI MK15: {e}")
            return False
    
    def _send_heartbeat(self):
        """Send heartbeat/connection packet to SIYI."""
        try:
            packet = SIYIProtocol.build_packet(SIYIProtocol.CMD_ACQUIRE_FW_VERSION)
            self.control_socket.sendto(packet, (self.transmitter_ip, self.control_port))
        except Exception as e:
            logger.debug(f"Heartbeat send error: {e}")
    
    def send_video_frame(self, frame: np.ndarray, quality: int = 80) -> bool:
        """
        Send video frame to SIYI transmitter.
        
        Args:
            frame: Video frame (numpy array)
            quality: JPEG compression quality (0-100)
            
        Returns:
            True if sent successfully
        """
        if not self.connected or not self.video_socket:
            return False
        
        try:
            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, encoded = cv2.imencode('.jpg', frame, encode_param)
            
            # Send via UDP (may need to fragment for large frames)
            frame_data = encoded.tobytes()
            
            # SIYI expects H.264 stream, but for simplicity we'll send MJPEG
            # In production, use hardware encoding to H.264
            
            max_packet_size = 1400  # MTU consideration
            
            if len(frame_data) <= max_packet_size:
                # Send as single packet
                self.video_socket.sendto(frame_data, (self.transmitter_ip, self.video_port))
            else:
                # Fragment into multiple packets
                num_packets = (len(frame_data) + max_packet_size - 1) // max_packet_size
                
                for i in range(num_packets):
                    start = i * max_packet_size
                    end = min((i + 1) * max_packet_size, len(frame_data))
                    packet = frame_data[start:end]
                    self.video_socket.sendto(packet, (self.transmitter_ip, self.video_port))
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending video frame: {e}")
            return False
    
    def send_telemetry(self, telemetry_data: dict) -> bool:
        """
        Send telemetry data to SIYI.
        
        Args:
            telemetry_data: Dictionary with telemetry information
            
        Returns:
            True if sent successfully
        """
        if not self.connected:
            return False
        
        try:
            # Format telemetry data (implement based on SIYI protocol)
            # This is a placeholder - actual implementation depends on SIYI specs
            
            logger.debug(f"Telemetry: {telemetry_data}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
            return False
    
    def control_gimbal(self, yaw_speed: int = 0, pitch_speed: int = 0) -> bool:
        """
        Control gimbal movement.
        
        Args:
            yaw_speed: Yaw rotation speed (-100 to 100)
            pitch_speed: Pitch rotation speed (-100 to 100)
            
        Returns:
            True if command sent successfully
        """
        if not self.connected:
            return False
        
        try:
            # Clamp speeds
            yaw_speed = max(-100, min(100, yaw_speed))
            pitch_speed = max(-100, min(100, pitch_speed))
            
            # Build gimbal speed control packet
            data = struct.pack('<bb', yaw_speed, pitch_speed)
            packet = SIYIProtocol.build_packet(SIYIProtocol.CMD_GIMBAL_SPEED, data)
            
            self.control_socket.sendto(packet, (self.transmitter_ip, self.control_port))
            return True
            
        except Exception as e:
            logger.error(f"Error controlling gimbal: {e}")
            return False
    
    def center_gimbal(self) -> bool:
        """Center the gimbal."""
        if not self.connected:
            return False
        
        try:
            packet = SIYIProtocol.build_packet(SIYIProtocol.CMD_CENTER)
            self.control_socket.sendto(packet, (self.transmitter_ip, self.control_port))
            logger.info("Gimbal centered")
            return True
            
        except Exception as e:
            logger.error(f"Error centering gimbal: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from SIYI MK15."""
        logger.info("Disconnecting from SIYI MK15")
        self.connected = False
        
        if self.video_socket:
            self.video_socket.close()
            self.video_socket = None
        
        if self.control_socket:
            self.control_socket.close()
            self.control_socket = None
        
        logger.info("Disconnected from SIYI MK15")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test configuration
    test_config = {
        'transmitter_ip': '192.168.144.25',
        'video_output_port': 5600,
        'control_port': 37260
    }
    
    # Test connection
    with SIYIMKController(test_config) as controller:
        logger.info("Testing SIYI MK15 connection...")
        time.sleep(2)
        
        # Test gimbal center
        controller.center_gimbal()
        time.sleep(1)
        
        logger.info("Test completed")
