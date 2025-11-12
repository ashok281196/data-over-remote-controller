"""
Camera capture module for Jetson devices.
Supports both CSI cameras (nvarguscamerasrc) and USB cameras (v4l2src).
"""

import cv2
import numpy as np
import logging
from typing import Optional, Callable
import threading
import queue

logger = logging.getLogger(__name__)


class JetsonCameraCapture:
    """Camera capture class optimized for Jetson devices."""
    
    def __init__(self, device_id: int = 0, width: int = 1920, height: int = 1080, 
                 fps: int = 30, source_type: str = "nvarguscamerasrc"):
        """
        Initialize camera capture.
        
        Args:
            device_id: Camera device ID
            width: Frame width
            height: Frame height
            fps: Frames per second
            source_type: "nvarguscamerasrc" for CSI or "v4l2src" for USB
        """
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.source_type = source_type
        self.cap = None
        self.running = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.frame_callbacks = []
        self.capture_thread = None
        
    def _create_gstreamer_pipeline(self) -> str:
        """Create GStreamer pipeline for Jetson."""
        if self.source_type == "nvarguscamerasrc":
            # CSI camera pipeline for Jetson
            pipeline = (
                f"nvarguscamerasrc sensor-id={self.device_id} ! "
                f"video/x-raw(memory:NVMM), width={self.width}, height={self.height}, "
                f"format=NV12, framerate={self.fps}/1 ! "
                f"nvvidconv flip-method=0 ! "
                f"video/x-raw, width={self.width}, height={self.height}, format=BGRx ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! appsink"
            )
        else:
            # USB camera pipeline
            pipeline = (
                f"v4l2src device=/dev/video{self.device_id} ! "
                f"video/x-raw, width={self.width}, height={self.height}, "
                f"framerate={self.fps}/1 ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! appsink"
            )
        return pipeline
    
    def start(self) -> bool:
        """Start camera capture."""
        try:
            if self.source_type == "nvarguscamerasrc":
                # Use GStreamer for CSI cameras
                pipeline = self._create_gstreamer_pipeline()
                self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            else:
                # Use standard OpenCV for USB cameras
                self.cap = cv2.VideoCapture(self.device_id)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.device_id}")
                return False
            
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            logger.info(f"Camera capture started: {self.width}x{self.height}@{self.fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False
    
    def _capture_loop(self):
        """Internal capture loop running in separate thread."""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Notify callbacks
                for callback in self.frame_callbacks:
                    try:
                        callback(frame)
                    except Exception as e:
                        logger.error(f"Error in frame callback: {e}")
                
                # Store latest frame (discard old if queue full)
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
                else:
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame)
                    except queue.Empty:
                        pass
            else:
                logger.warning("Failed to read frame from camera")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame."""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def register_callback(self, callback: Callable[[np.ndarray], None]):
        """Register a callback function to receive frames."""
        self.frame_callbacks.append(callback)
    
    def stop(self):
        """Stop camera capture."""
        self.running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        logger.info("Camera capture stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
