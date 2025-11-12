"""
Camera capture module for Jetson devices with GStreamer support.
Supports both standard USB cameras and CSI cameras on Jetson platforms.
"""

import cv2
import numpy as np
import threading
import queue
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class JetsonCamera:
    """
    Camera capture class optimized for Jetson devices.
    Supports hardware-accelerated capture using GStreamer.
    """
    
    def __init__(self, config: dict):
        """
        Initialize camera with configuration.
        
        Args:
            config: Camera configuration dictionary
        """
        self.config = config
        self.camera = None
        self.frame_queue = queue.Queue(maxsize=30)
        self.capture_thread = None
        self.running = False
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Camera settings
        self.device_id = config.get('device_id', 0)
        self.width = config.get('width', 1920)
        self.height = config.get('height', 1080)
        self.fps = config.get('fps', 30)
        self.use_gstreamer = config.get('use_gstreamer', True)
        
    def _build_gstreamer_pipeline(self) -> str:
        """
        Build GStreamer pipeline for Jetson hardware acceleration.
        
        Returns:
            GStreamer pipeline string
        """
        # Check if custom pipeline is provided
        if 'gstreamer_pipeline' in self.config:
            pipeline = self.config['gstreamer_pipeline'].format(
                device_id=self.device_id,
                width=self.width,
                height=self.height,
                fps=self.fps
            )
            return pipeline
        
        # Default pipeline for CSI camera (e.g., Raspberry Pi Camera on Jetson)
        pipeline = (
            f"nvarguscamerasrc sensor-id={self.device_id} ! "
            f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
            f"framerate={self.fps}/1 ! "
            f"nvvidconv ! "
            f"video/x-raw, format=BGRx ! "
            f"videoconvert ! "
            f"video/x-raw, format=BGR ! "
            f"appsink"
        )
        return pipeline
    
    def open(self) -> bool:
        """
        Open camera device.
        
        Returns:
            True if camera opened successfully, False otherwise
        """
        try:
            if self.use_gstreamer:
                pipeline = self._build_gstreamer_pipeline()
                logger.info(f"Opening camera with GStreamer pipeline: {pipeline}")
                self.camera = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            else:
                logger.info(f"Opening camera device {self.device_id}")
                self.camera = cv2.VideoCapture(self.device_id)
                
                # Set camera properties for standard V4L2 capture
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                
                # Try to set format if specified
                if 'format' in self.config:
                    fourcc = cv2.VideoWriter_fourcc(*self.config['format'])
                    self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)
            
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
            
            # Verify camera properties
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"Camera opened: {actual_width}x{actual_height} @ {actual_fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Error opening camera: {e}")
            return False
    
    def _capture_loop(self):
        """Background thread for continuous frame capture."""
        logger.info("Starting capture loop")
        
        while self.running:
            try:
                ret, frame = self.camera.read()
                
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Update FPS counter
                self.frame_count += 1
                current_time = time.time()
                elapsed = current_time - self.last_fps_time
                
                if elapsed >= 1.0:
                    self.current_fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.last_fps_time = current_time
                    logger.debug(f"Camera FPS: {self.current_fps:.2f}")
                
                # Add frame to queue (drop oldest if full)
                try:
                    self.frame_queue.put_nowait((frame, current_time))
                except queue.Full:
                    # Remove oldest frame and add new one
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait((frame, current_time))
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                time.sleep(0.1)
        
        logger.info("Capture loop stopped")
    
    def start(self) -> bool:
        """
        Start camera capture in background thread.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Camera already running")
            return True
        
        if not self.camera or not self.camera.isOpened():
            if not self.open():
                return False
        
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        logger.info("Camera capture started")
        return True
    
    def read(self, timeout: float = 1.0) -> Optional[Tuple[np.ndarray, float]]:
        """
        Read the latest frame from the queue.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (frame, timestamp) or None if no frame available
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_latest_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """
        Get the most recent frame, discarding older ones.
        
        Returns:
            Tuple of (frame, timestamp) or None if no frame available
        """
        frame_data = None
        
        # Get all available frames, keeping only the latest
        while True:
            try:
                frame_data = self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        return frame_data
    
    def get_fps(self) -> float:
        """Get current capture FPS."""
        return self.current_fps
    
    def stop(self):
        """Stop camera capture."""
        logger.info("Stopping camera capture")
        self.running = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        
        if self.camera:
            self.camera.release()
            self.camera = None
        
        logger.info("Camera capture stopped")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def test_camera(config: dict):
    """
    Test camera capture and display frames.
    
    Args:
        config: Camera configuration dictionary
    """
    logger.info("Starting camera test")
    
    with JetsonCamera(config) as camera:
        cv2.namedWindow('Camera Test', cv2.WINDOW_NORMAL)
        
        while True:
            frame_data = camera.read(timeout=1.0)
            
            if frame_data is None:
                logger.warning("No frame received")
                continue
            
            frame, timestamp = frame_data
            
            # Add FPS overlay
            fps = camera.get_fps()
            cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow('Camera Test', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        
        cv2.destroyAllWindows()
    
    logger.info("Camera test completed")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test configuration
    test_config = {
        'device_id': 0,
        'width': 1280,
        'height': 720,
        'fps': 30,
        'use_gstreamer': False  # Set to True for Jetson with CSI camera
    }
    
    test_camera(test_config)
