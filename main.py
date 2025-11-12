#!/usr/bin/env python3
"""
Main Orchestrator Script
Manages all components: camera capture, SIYI streaming, LiveKit streaming, telemetry, and web UI.
"""

import argparse
import logging
import os
import sys
import time
import signal
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from camera_capture import JetsonCamera
from siyi_controller import SIYIMKController
from livekit_streamer import LiveKitStreamManager
from telemetry import JetsonTelemetry
from web_server import WebServer


class StreamOrchestrator:
    """
    Main orchestrator for Jetson camera streaming system.
    Coordinates all components and manages their lifecycle.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        
        # Components
        self.camera = None
        self.siyi = None
        self.livekit = None
        self.telemetry = None
        self.web_server = None
        
        # State
        self.running = False
        self.frame_count = 0
        self.start_time = None
        
        logger.info("Stream Orchestrator initialized")
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        # Load environment variables
        load_dotenv()
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Override with environment variables if present
        if 'LIVEKIT_URL' in os.environ:
            config['livekit']['url'] = os.environ['LIVEKIT_URL']
        if 'LIVEKIT_API_KEY' in os.environ:
            config['livekit']['api_key'] = os.environ['LIVEKIT_API_KEY']
        if 'LIVEKIT_API_SECRET' in os.environ:
            config['livekit']['api_secret'] = os.environ['LIVEKIT_API_SECRET']
        if 'SIYI_TRANSMITTER_IP' in os.environ:
            config['siyi']['transmitter_ip'] = os.environ['SIYI_TRANSMITTER_IP']
        
        return config
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        
        # Create logs directory if needed
        if log_config.get('log_to_file', False):
            log_file = log_config.get('log_file', 'logs/stream.log')
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
        else:
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        global logger
        logger = logging.getLogger(__name__)
    
    def _initialize_components(self) -> bool:
        """
        Initialize all components.
        
        Returns:
            True if all components initialized successfully
        """
        logger.info("Initializing components...")
        
        try:
            # Initialize camera
            logger.info("Initializing camera...")
            self.camera = JetsonCamera(self.config['camera'])
            if not self.camera.open():
                logger.error("Failed to open camera")
                return False
            self.camera.start()
            logger.info("✓ Camera initialized")
            
            # Initialize SIYI controller (if enabled)
            if self.config.get('siyi', {}).get('enabled', True):
                logger.info("Initializing SIYI MK15 controller...")
                self.siyi = SIYIMKController(self.config['siyi'])
                if not self.siyi.connect():
                    logger.warning("Failed to connect to SIYI MK15 (continuing anyway)")
                else:
                    logger.info("✓ SIYI MK15 connected")
            
            # Initialize LiveKit streamer (if enabled)
            if self.config.get('livekit', {}).get('enabled', True):
                logger.info("Initializing LiveKit streamer...")
                self.livekit = LiveKitStreamManager(self.config['livekit'])
                # LiveKit initialization happens in background
                logger.info("✓ LiveKit streamer initialized")
            
            # Initialize telemetry
            if self.config.get('telemetry', {}).get('enabled', True):
                logger.info("Initializing telemetry collector...")
                self.telemetry = JetsonTelemetry(self.config['telemetry'])
                self.telemetry.start()
                logger.info("✓ Telemetry collector started")
            
            # Initialize web server (if enabled)
            if self.config.get('web_ui', {}).get('enabled', True):
                logger.info("Initializing web server...")
                self.web_server = WebServer(self.config['web_ui'])
                self.web_server.run_threaded()
                logger.info(f"✓ Web server started on {self.config['web_ui']['host']}:{self.config['web_ui']['port']}")
            
            logger.info("All components initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}", exc_info=True)
            return False
    
    def _process_frame(self, frame, timestamp):
        """
        Process a single frame and distribute to outputs.
        
        Args:
            frame: Video frame
            timestamp: Frame timestamp
        """
        self.frame_count += 1
        
        # Send to SIYI transmitter
        if self.siyi and self.siyi.connected:
            self.siyi.send_video_frame(frame, quality=80)
        
        # Send to LiveKit
        if self.livekit:
            self.livekit.send_frame(frame)
        
        # Update web server
        if self.web_server:
            self.web_server.update_frame(frame)
    
    def _update_telemetry(self):
        """Update telemetry data to all outputs."""
        if not self.telemetry:
            return
        
        # Update camera FPS
        if self.camera:
            self.telemetry.update_camera_fps(self.camera.get_fps())
        
        # Calculate stream FPS
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                stream_fps = self.frame_count / elapsed
                self.telemetry.update_stream_fps(stream_fps)
        
        # Get current telemetry data
        telemetry_data = self.telemetry.get_current_data()
        
        # Add connection status
        telemetry_data['siyi_connected'] = self.siyi.connected if self.siyi else False
        telemetry_data['livekit_connected'] = (
            self.livekit.streamer.connected 
            if self.livekit and self.livekit.streamer 
            else False
        )
        
        # Send to SIYI
        if self.siyi and self.siyi.connected:
            self.siyi.send_telemetry(telemetry_data)
        
        # Send to LiveKit
        if self.livekit:
            self.livekit.send_telemetry(telemetry_data)
        
        # Send to web server
        if self.web_server:
            self.web_server.update_telemetry(telemetry_data)
    
    def _main_loop(self):
        """Main processing loop."""
        logger.info("Starting main processing loop...")
        self.start_time = time.time()
        self.frame_count = 0
        
        last_telemetry_update = time.time()
        telemetry_interval = 1.0 / self.config.get('telemetry', {}).get('rate_hz', 5)
        
        try:
            while self.running:
                # Get frame from camera
                frame_data = self.camera.get_latest_frame()
                
                if frame_data is None:
                    time.sleep(0.01)
                    continue
                
                frame, timestamp = frame_data
                
                # Process frame
                self._process_frame(frame, timestamp)
                
                # Update telemetry periodically
                current_time = time.time()
                if current_time - last_telemetry_update >= telemetry_interval:
                    self._update_telemetry()
                    last_telemetry_update = current_time
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
    
    def start(self):
        """Start the streaming system."""
        logger.info("=" * 60)
        logger.info("Starting Jetson Camera Streaming System")
        logger.info("=" * 60)
        
        if not self._initialize_components():
            logger.error("Failed to initialize components")
            return False
        
        self.running = True
        
        # Print status
        logger.info("")
        logger.info("System Status:")
        logger.info(f"  Camera: {'✓ Running' if self.camera else '✗ Not initialized'}")
        logger.info(f"  SIYI MK15: {'✓ Connected' if self.siyi and self.siyi.connected else '✗ Not connected'}")
        logger.info(f"  LiveKit: {'✓ Enabled' if self.livekit else '✗ Disabled'}")
        logger.info(f"  Telemetry: {'✓ Running' if self.telemetry else '✗ Disabled'}")
        logger.info(f"  Web UI: {'✓ Running' if self.web_server else '✗ Disabled'}")
        
        if self.web_server:
            logger.info("")
            logger.info(f"🌐 Web UI: http://localhost:{self.config['web_ui']['port']}")
        
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # Run main loop
        self._main_loop()
        
        return True
    
    def stop(self):
        """Stop the streaming system."""
        logger.info("Stopping streaming system...")
        self.running = False
        
        # Stop components in reverse order
        if self.telemetry:
            self.telemetry.stop()
        
        if self.livekit:
            self.livekit.stop()
        
        if self.siyi:
            self.siyi.disconnect()
        
        if self.camera:
            self.camera.stop()
        
        # Print final statistics
        if self.start_time:
            total_time = time.time() - self.start_time
            avg_fps = self.frame_count / total_time if total_time > 0 else 0
            
            logger.info("")
            logger.info("Session Statistics:")
            logger.info(f"  Total frames: {self.frame_count}")
            logger.info(f"  Duration: {total_time:.1f}s")
            logger.info(f"  Average FPS: {avg_fps:.2f}")
        
        logger.info("System stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Jetson Camera Streaming with SIYI MK15 and LiveKit'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file '{args.config}' not found")
        print("Please create a configuration file or specify a different path with -c")
        return 1
    
    # Create orchestrator
    orchestrator = StreamOrchestrator(args.config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received signal, shutting down...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start streaming
    try:
        orchestrator.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        orchestrator.stop()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
