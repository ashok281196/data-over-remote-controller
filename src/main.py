"""
Main application orchestrator for Jetson camera streaming with SIYI MK15.
"""

import asyncio
import logging
import signal
import sys
import yaml
from pathlib import Path
from typing import Optional
import numpy as np

from camera_capture import JetsonCameraCapture
from siyi_mk15 import SIYIMK15
from livekit_streamer import LiveKitStreamer
from telemetry_handler import TelemetryHandler
from web_ui import WebUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/jetson_stream.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class JetsonStreamApplication:
    """Main application class."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize application with configuration."""
        self.config = self.load_config(config_path)
        self.running = False
        
        # Initialize components
        self.camera: Optional[JetsonCameraCapture] = None
        self.siyi: Optional[SIYIMK15] = None
        self.livekit: Optional[LiveKitStreamer] = None
        self.telemetry_handler: Optional[TelemetryHandler] = None
        self.web_ui: Optional[WebUI] = None
        
        # Video source for LiveKit
        self.video_source = None
        
        # Event loop for async operations
        self.event_loop = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.running = False
    
    async def initialize(self) -> bool:
        """Initialize all components."""
        try:
            # Create logs directory
            Path("logs").mkdir(exist_ok=True)
            
            # Initialize camera
            camera_cfg = self.config.get('camera', {})
            self.camera = JetsonCameraCapture(
                device_id=camera_cfg.get('device_id', 0),
                width=camera_cfg.get('width', 1920),
                height=camera_cfg.get('height', 1080),
                fps=camera_cfg.get('fps', 30),
                source_type=camera_cfg.get('source_type', 'nvarguscamerasrc')
            )
            
            if not self.camera.start():
                logger.error("Failed to start camera")
                return False
            
            # Initialize SIYI MK15
            siyi_cfg = self.config.get('siyi_mk15', {})
            self.siyi = SIYIMK15(
                serial_port=siyi_cfg.get('serial_port', '/dev/ttyUSB0'),
                baudrate=siyi_cfg.get('baudrate', 115200)
            )
            
            if not self.siyi.connect():
                logger.warning("Failed to connect to SIYI MK15, continuing without it")
            else:
                # Start video transmission
                if siyi_cfg.get('enable_video_transmission', True):
                    quality = siyi_cfg.get('video_quality', 'high')
                    self.siyi.start_video_transmission(quality)
                    logger.info(f"SIYI MK15 video transmission started ({quality} quality)")
            
            # Initialize LiveKit
            livekit_cfg = self.config.get('livekit', {})
            self.livekit = LiveKitStreamer(
                url=livekit_cfg.get('url', ''),
                api_key=livekit_cfg.get('api_key', ''),
                api_secret=livekit_cfg.get('api_secret', ''),
                room_name=livekit_cfg.get('room_name', 'jetson-camera-stream'),
                participant_name=livekit_cfg.get('participant_name', 'jetson-camera')
            )
            
            if await self.livekit.connect():
                # Create video track
                self.video_source = self.livekit.create_video_track(
                    width=camera_cfg.get('width', 1920),
                    height=camera_cfg.get('height', 1080),
                    fps=camera_cfg.get('fps', 30)
                )
                logger.info("LiveKit connected and video track created")
            else:
                logger.warning("Failed to connect to LiveKit, continuing without it")
            
            # Initialize telemetry handler
            telemetry_cfg = self.config.get('telemetry', {})
            self.telemetry_handler = TelemetryHandler(
                update_rate=telemetry_cfg.get('update_rate', 10),
                include_gps=telemetry_cfg.get('include_gps', True),
                include_attitude=telemetry_cfg.get('include_attitude', True),
                include_battery=telemetry_cfg.get('include_battery', True),
                include_system_stats=telemetry_cfg.get('include_system_stats', True)
            )
            self.telemetry_handler.start()
            
            # Setup SIYI telemetry callback
            if self.siyi:
                self.siyi.register_telemetry_callback(
                    self.telemetry_handler.update_from_siyi
                )
            
            # Setup telemetry callbacks
            self.telemetry_handler.register_callback(self.on_telemetry_update)
            
            # Initialize Web UI
            ui_cfg = self.config.get('ui', {})
            self.web_ui = WebUI(
                host=ui_cfg.get('host', '0.0.0.0'),
                port=ui_cfg.get('port', 8080)
            )
            
            # Setup camera frame callback
            self.camera.register_callback(self.on_frame_received)
            
            logger.info("All components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing application: {e}")
            return False
    
    def on_frame_received(self, frame: np.ndarray):
        """Handle new frame from camera."""
        try:
            # Send to LiveKit
            if self.livekit and self.video_source and self.livekit.connected:
                self.livekit.send_frame(frame, self.video_source)
            
            # Update Web UI
            if self.web_ui:
                self.web_ui.update_frame(frame)
            
            # Update frame rate in telemetry
            if self.telemetry_handler:
                self.telemetry_handler.update_frame_rate()
                
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
    
    def on_telemetry_update(self, telemetry: dict):
        """Handle telemetry update."""
        try:
            # Update Web UI (thread-safe)
            if self.web_ui:
                self.web_ui.update_telemetry(telemetry)
            
            # Send to LiveKit (schedule in event loop if available)
            if self.livekit and self.livekit.connected and self.event_loop:
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.livekit.send_telemetry(telemetry),
                        self.event_loop
                    )
                except Exception as e:
                    logger.error(f"Error scheduling telemetry send: {e}")
                
        except Exception as e:
            logger.error(f"Error processing telemetry: {e}")
    
    async def run(self):
        """Run the main application loop."""
        if not await self.initialize():
            logger.error("Failed to initialize application")
            return
        
        # Store event loop for thread-safe async operations
        self.event_loop = asyncio.get_event_loop()
        
        self.running = True
        logger.info("Application started")
        
        # Start Web UI in background
        import threading
        ui_thread = threading.Thread(target=self.web_ui.run, daemon=True)
        ui_thread.start()
        logger.info(f"Web UI started on http://{self.config.get('ui', {}).get('host', '0.0.0.0')}:{self.config.get('ui', {}).get('port', 8080)}")
        
        # Request telemetry periodically from SIYI
        if self.siyi:
            async def request_telemetry_loop():
                while self.running:
                    self.siyi.request_telemetry()
                    await asyncio.sleep(1.0 / self.telemetry_handler.update_rate)
            
            asyncio.create_task(request_telemetry_loop())
        
        # Main loop
        try:
            while self.running:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown all components."""
        logger.info("Shutting down application...")
        self.running = False
        
        if self.camera:
            self.camera.stop()
        
        if self.siyi:
            self.siyi.disconnect()
        
        if self.livekit:
            await self.livekit.disconnect()
        
        if self.telemetry_handler:
            self.telemetry_handler.stop()
        
        logger.info("Application shutdown complete")


async def main():
    """Main entry point."""
    app = JetsonStreamApplication()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
