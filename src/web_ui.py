"""
Web UI for monitoring camera stream and telemetry data.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import logging
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
import base64

logger = logging.getLogger(__name__)


class WebUI:
    """Web UI server for camera stream and telemetry monitoring."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        """
        Initialize Web UI.
        
        Args:
            host: Host address
            port: Port number
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="Jetson Camera Stream")
        self.websocket_connections: List[WebSocket] = []
        self.current_frame: Optional[np.ndarray] = None
        self.current_telemetry: Dict[str, Any] = {}
        self.setup_routes()
    
    def setup_routes(self):
        """Set up FastAPI routes."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index():
            return self.get_html_ui()
        
        @self.app.get("/api/telemetry")
        async def get_telemetry():
            """Get current telemetry data."""
            return self.current_telemetry
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            try:
                while True:
                    # Send telemetry updates
                    await websocket.send_json({
                        "type": "telemetry",
                        "data": self.current_telemetry
                    })
                    await asyncio.sleep(0.1)  # 10 Hz update rate
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
        
        @self.app.get("/stream")
        async def video_stream():
            """Video stream endpoint (MJPEG)."""
            return StreamingResponse(
                self.generate_frames(),
                media_type="multipart/x-mixed-replace; boundary=frame"
            )
    
    def get_html_ui(self) -> str:
        """Get HTML UI content."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jetson Camera Stream - SIYI MK15</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .video-panel {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .video-panel h2 {
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .video-container {
            position: relative;
            width: 100%;
            padding-bottom: 56.25%; /* 16:9 aspect ratio */
            background: #000;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .video-container img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        
        .telemetry-panel {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .telemetry-panel h2 {
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .telemetry-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
        }
        
        .telemetry-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .telemetry-item label {
            display: block;
            font-weight: bold;
            color: #555;
            margin-bottom: 5px;
            font-size: 0.9em;
        }
        
        .telemetry-item value {
            display: block;
            font-size: 1.2em;
            color: #333;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-connected {
            background: #28a745;
            box-shadow: 0 0 10px #28a745;
        }
        
        .status-disconnected {
            background: #dc3545;
        }
        
        .controls {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        
        .controls h2 {
            margin-bottom: 15px;
            color: #667eea;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: #667eea;
            color: white;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        @media (max-width: 1024px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚁 Jetson Camera Stream</h1>
            <p>SIYI MK15 Transmitter & LiveKit Integration</p>
        </div>
        
        <div class="main-content">
            <div class="video-panel">
                <h2>📹 Video Stream</h2>
                <div class="video-container">
                    <img id="videoStream" src="/stream" alt="Camera Stream">
                </div>
            </div>
            
            <div class="telemetry-panel">
                <h2>📊 Telemetry Data</h2>
                <div class="telemetry-grid" id="telemetryGrid">
                    <div class="telemetry-item">
                        <label>Connection Status</label>
                        <value><span class="status-indicator" id="statusIndicator"></span><span id="statusText">Connecting...</span></value>
                    </div>
                    <div class="telemetry-item">
                        <label>GPS Latitude</label>
                        <value id="gpsLat">0.0000°</value>
                    </div>
                    <div class="telemetry-item">
                        <label>GPS Longitude</label>
                        <value id="gpsLon">0.0000°</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Altitude</label>
                        <value id="altitude">0.0 m</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Roll</label>
                        <value id="roll">0.0°</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Pitch</label>
                        <value id="pitch">0.0°</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Yaw</label>
                        <value id="yaw">0.0°</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Frame Rate</label>
                        <value id="frameRate">0.0 fps</value>
                    </div>
                    <div class="telemetry-item">
                        <label>CPU Usage</label>
                        <value id="cpuUsage">0.0%</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Memory Usage</label>
                        <value id="memoryUsage">0.0%</value>
                    </div>
                    <div class="telemetry-item">
                        <label>Temperature</label>
                        <value id="temperature">0.0°C</value>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <h2>🎮 Controls</h2>
            <div class="button-group">
                <button onclick="startStream()">Start Stream</button>
                <button onclick="stopStream()">Stop Stream</button>
                <button onclick="refreshTelemetry()">Refresh</button>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                document.getElementById('statusIndicator').className = 'status-indicator status-connected';
                document.getElementById('statusText').textContent = 'Connected';
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'telemetry') {
                    updateTelemetry(data.data);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                document.getElementById('statusIndicator').className = 'status-indicator status-disconnected';
                document.getElementById('statusText').textContent = 'Error';
            };
            
            ws.onclose = () => {
                document.getElementById('statusIndicator').className = 'status-indicator status-disconnected';
                document.getElementById('statusText').textContent = 'Disconnected';
                // Reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        function updateTelemetry(data) {
            document.getElementById('gpsLat').textContent = data.gps_lat?.toFixed(4) + '°' || '0.0000°';
            document.getElementById('gpsLon').textContent = data.gps_lon?.toFixed(4) + '°' || '0.0000°';
            document.getElementById('altitude').textContent = (data.altitude?.toFixed(1) || '0.0') + ' m';
            document.getElementById('roll').textContent = (data.roll?.toFixed(1) || '0.0') + '°';
            document.getElementById('pitch').textContent = (data.pitch?.toFixed(1) || '0.0') + '°';
            document.getElementById('yaw').textContent = (data.yaw?.toFixed(1) || '0.0') + '°';
            document.getElementById('frameRate').textContent = (data.frame_rate?.toFixed(1) || '0.0') + ' fps';
            document.getElementById('cpuUsage').textContent = (data.cpu_usage?.toFixed(1) || '0.0') + '%';
            document.getElementById('memoryUsage').textContent = (data.memory_usage?.toFixed(1) || '0.0') + '%';
            document.getElementById('temperature').textContent = (data.temperature?.toFixed(1) || '0.0') + '°C';
        }
        
        function startStream() {
            alert('Stream started (implement API call)');
        }
        
        function stopStream() {
            alert('Stream stopped (implement API call)');
        }
        
        function refreshTelemetry() {
            fetch('/api/telemetry')
                .then(response => response.json())
                .then(data => updateTelemetry(data))
                .catch(error => console.error('Error fetching telemetry:', error));
        }
        
        // Initialize on page load
        connectWebSocket();
        refreshTelemetry();
        setInterval(refreshTelemetry, 5000); // Refresh every 5 seconds
    </script>
</body>
</html>
        """
    
    async def generate_frames(self):
        """Generate video frames for MJPEG stream."""
        while True:
            if self.current_frame is not None:
                try:
                    # Encode frame as JPEG
                    ret, buffer = cv2.imencode('.jpg', self.current_frame, 
                                              [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                except Exception as e:
                    logger.error(f"Error encoding frame: {e}")
            await asyncio.sleep(1.0 / 30.0)  # 30 FPS
    
    def update_frame(self, frame: np.ndarray):
        """Update current frame for streaming."""
        self.current_frame = frame.copy()
    
    def update_telemetry(self, telemetry: Dict[str, Any]):
        """Update telemetry data."""
        self.current_telemetry = telemetry
        # Broadcast to all WebSocket connections
        asyncio.create_task(self.broadcast_telemetry(telemetry))
    
    async def broadcast_telemetry(self, telemetry: Dict[str, Any]):
        """Broadcast telemetry to all WebSocket connections."""
        message = json.dumps({"type": "telemetry", "data": telemetry})
        disconnected = []
        for connection in self.websocket_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            if conn in self.websocket_connections:
                self.websocket_connections.remove(conn)
    
    def run(self):
        """Run the web UI server."""
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)
