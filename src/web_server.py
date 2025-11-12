"""
Web Server Module
Provides web UI for monitoring camera streams and telemetry data.
Uses Flask and SocketIO for real-time updates.
"""

from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import numpy as np
import logging
import json
from typing import Optional, Dict
import threading
import time

logger = logging.getLogger(__name__)


class WebServer:
    """
    Web server for camera streaming and telemetry monitoring.
    Provides REST API and WebSocket for real-time updates.
    """
    
    def __init__(self, config: dict):
        """
        Initialize web server.
        
        Args:
            config: Web server configuration
        """
        self.config = config
        self.host = config.get('host', '0.0.0.0')
        self.port = config.get('port', 8080)
        self.debug = config.get('debug', False)
        
        # Flask app
        self.app = Flask(__name__, 
                        template_folder='../web/templates',
                        static_folder='../web/static')
        self.app.config['SECRET_KEY'] = 'jetson-stream-secret'
        
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # State
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.telemetry_data = {}
        self.telemetry_lock = threading.Lock()
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"Web server initialized on {self.host}:{self.port}")
    
    def _setup_routes(self):
        """Setup Flask routes and SocketIO handlers."""
        
        @self.app.route('/')
        def index():
            """Main page."""
            return render_template('index.html')
        
        @self.app.route('/api/status')
        def status():
            """Get system status."""
            return jsonify({
                'status': 'running',
                'timestamp': time.time()
            })
        
        @self.app.route('/api/telemetry')
        def get_telemetry():
            """Get current telemetry data."""
            with self.telemetry_lock:
                return jsonify(self.telemetry_data)
        
        @self.app.route('/video_feed')
        def video_feed():
            """Video streaming route."""
            return Response(
                self._generate_frames(),
                mimetype='multipart/x-mixed-replace; boundary=frame'
            )
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            logger.info(f"Client connected")
            emit('status', {'status': 'connected'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            logger.info(f"Client disconnected")
        
        @self.socketio.on('request_telemetry')
        def handle_telemetry_request():
            """Handle telemetry data request."""
            with self.telemetry_lock:
                emit('telemetry_update', self.telemetry_data)
    
    def _generate_frames(self):
        """
        Generator for video streaming.
        Yields JPEG frames for MJPEG stream.
        """
        while True:
            with self.frame_lock:
                if self.current_frame is None:
                    # Send blank frame if no frame available
                    blank = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(blank, 'No Camera Feed', (200, 240),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    _, buffer = cv2.imencode('.jpg', blank)
                else:
                    _, buffer = cv2.imencode('.jpg', self.current_frame,
                                            [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.033)  # ~30 fps
    
    def update_frame(self, frame: np.ndarray):
        """
        Update current video frame.
        
        Args:
            frame: Video frame (numpy array)
        """
        with self.frame_lock:
            self.current_frame = frame.copy()
    
    def update_telemetry(self, telemetry: Dict):
        """
        Update telemetry data and broadcast to connected clients.
        
        Args:
            telemetry: Telemetry data dictionary
        """
        with self.telemetry_lock:
            self.telemetry_data = telemetry.copy()
        
        # Broadcast to all connected clients
        self.socketio.emit('telemetry_update', telemetry)
    
    def run(self):
        """Run the web server (blocking)."""
        logger.info(f"Starting web server on {self.host}:{self.port}")
        self.socketio.run(
            self.app,
            host=self.host,
            port=self.port,
            debug=self.debug,
            allow_unsafe_werkzeug=True
        )
    
    def run_threaded(self):
        """Run the web server in a background thread."""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        logger.info("Web server started in background thread")
        return thread


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test configuration
    test_config = {
        'host': '0.0.0.0',
        'port': 8080,
        'debug': True
    }
    
    # Create and run server
    server = WebServer(test_config)
    
    # Simulate frame updates
    def update_test_frames():
        frame_count = 0
        while True:
            # Create test frame
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f'Frame: {frame_count}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            server.update_frame(frame)
            
            # Update telemetry
            server.update_telemetry({
                'frame_count': frame_count,
                'cpu_usage': 45.2,
                'memory_usage': 62.8,
                'timestamp': time.time()
            })
            
            frame_count += 1
            time.sleep(0.033)
    
    # Start frame update thread
    threading.Thread(target=update_test_frames, daemon=True).start()
    
    # Run server
    server.run()
