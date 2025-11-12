# Project Summary: Jetson Camera Streaming System

## Overview

A complete camera streaming solution for NVIDIA Jetson devices that enables:
- Hardware-accelerated video capture
- Wireless transmission via SIYI MK15
- Cloud streaming via LiveKit
- Real-time telemetry monitoring
- Modern web UI for system monitoring

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Jetson Device                             │
│  ┌─────────────┐                                            │
│  │   Camera    │                                            │
│  │ (CSI/USB)   │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Camera Capture Module                         │   │
│  │  (GStreamer Hardware Acceleration)                   │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Main Orchestrator                          │   │
│  │     (Frame Distribution & Management)                │   │
│  └──┬────────────┬──────────────┬───────────────────┬──┘   │
│     │            │              │                   │       │
│     ▼            ▼              ▼                   ▼       │
│  ┌──────┐   ┌────────┐   ┌──────────┐      ┌──────────┐  │
│  │SIYI  │   │LiveKit │   │Telemetry │      │Web Server│  │
│  │MK15  │   │Streamer│   │Collector │      │          │  │
│  └──┬───┘   └───┬────┘   └────┬─────┘      └────┬─────┘  │
│     │           │              │                  │        │
└─────┼───────────┼──────────────┼──────────────────┼────────┘
      │           │              │                  │
      ▼           ▼              ▼                  ▼
 ┌────────┐  ┌─────────┐   ┌─────────┐      ┌──────────┐
 │ SIYI   │  │LiveKit  │   │All      │      │Web       │
 │Ground  │  │Cloud    │   │Output   │      │Browser   │
 │Station │  │Server   │   │Streams  │      │          │
 └────────┘  └─────────┘   └─────────┘      └──────────┘
```

## Components

### 1. Camera Capture (`camera_capture.py`)
- **Purpose**: Capture video from Jetson cameras
- **Features**:
  - GStreamer hardware acceleration
  - CSI and USB camera support
  - Thread-safe frame buffering
  - FPS monitoring
- **Key Classes**: `JetsonCamera`

### 2. SIYI Controller (`siyi_controller.py`)
- **Purpose**: Communicate with SIYI MK15 ground station
- **Features**:
  - SIYI SDK protocol implementation
  - Video frame transmission (UDP)
  - Telemetry data sending
  - Gimbal control commands
- **Key Classes**: `SIYIMKController`, `SIYIProtocol`

### 3. LiveKit Streamer (`livekit_streamer.py`)
- **Purpose**: Cloud streaming via LiveKit
- **Features**:
  - WebRTC-based streaming
  - Real-time video publishing
  - Data channel for telemetry
  - Room management
- **Key Classes**: `LiveKitStreamer`, `LiveKitStreamManager`

### 4. Telemetry Collector (`telemetry.py`)
- **Purpose**: System monitoring and metrics collection
- **Features**:
  - CPU/GPU usage monitoring
  - Memory statistics
  - Temperature readings (Jetson-specific)
  - Network statistics
  - Custom metrics (FPS, etc.)
- **Key Classes**: `JetsonTelemetry`

### 5. Web Server (`web_server.py`)
- **Purpose**: Web UI for monitoring
- **Features**:
  - Flask-based REST API
  - WebSocket for real-time updates
  - MJPEG video streaming
  - Responsive dashboard
- **Key Classes**: `WebServer`

### 6. Main Orchestrator (`main.py`)
- **Purpose**: Coordinate all components
- **Features**:
  - Component lifecycle management
  - Configuration loading
  - Frame distribution
  - Error handling and logging
- **Key Classes**: `StreamOrchestrator`

## File Structure

```
data-over-remote-controller/
├── main.py                      # Main entry point
├── config.yaml                  # Configuration file
├── requirements.txt             # Python dependencies
├── setup.sh                     # Automated setup script
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
│
├── README.md                    # Project overview
├── SETUP.md                     # Detailed setup guide
├── QUICKSTART.md               # Quick start guide
├── PROJECT_SUMMARY.md          # This file
│
├── src/                         # Source code
│   ├── __init__.py
│   ├── camera_capture.py       # Camera interface
│   ├── siyi_controller.py      # SIYI MK15 control
│   ├── livekit_streamer.py     # LiveKit streaming
│   ├── telemetry.py            # Telemetry collection
│   └── web_server.py           # Web UI server
│
├── web/                         # Web UI files
│   ├── templates/
│   │   └── index.html          # Main UI page
│   └── static/
│       ├── style.css           # Styles
│       └── app.js              # JavaScript
│
└── scripts/                     # Utility scripts
    ├── check_system.sh         # System check
    ├── test_camera.sh          # Camera test
    └── install_jetson_stats.sh # Install monitoring tools
```

## Configuration

### Main Configuration (`config.yaml`)

```yaml
camera:          # Camera settings
siyi:            # SIYI MK15 settings
livekit:         # LiveKit settings
telemetry:       # Telemetry settings
web_ui:          # Web UI settings
logging:         # Logging settings
```

### Environment Variables (`.env`)

```bash
LIVEKIT_URL              # LiveKit server URL
LIVEKIT_API_KEY          # LiveKit API key
LIVEKIT_API_SECRET       # LiveKit API secret
SIYI_TRANSMITTER_IP      # SIYI MK15 IP address
CAMERA_DEVICE_ID         # Camera device ID
```

## Data Flow

### Video Stream Flow
1. **Camera** captures frames → Hardware acceleration (GStreamer)
2. **Camera Capture** module → Frame buffer (thread-safe queue)
3. **Main Orchestrator** reads frames → Distributes to outputs
4. **Outputs**:
   - SIYI: UDP transmission to ground station
   - LiveKit: WebRTC streaming to cloud
   - Web UI: MJPEG streaming to browser

### Telemetry Flow
1. **Telemetry Collector** gathers system metrics (periodic)
2. **Data enrichment** with camera/stream FPS
3. **Distribution**:
   - SIYI: Sent with video stream
   - LiveKit: Sent via data channel
   - Web UI: Broadcast via WebSocket

## Performance Characteristics

### Expected Performance (Jetson Nano)
- **Resolution**: 1280x720 @ 30 FPS
- **CPU Usage**: 40-60%
- **Memory**: ~500-800 MB
- **Latency**: 
  - SIYI: <100ms
  - LiveKit: 200-500ms (network dependent)
  - Web UI: <50ms (local network)

### Expected Performance (Jetson Xavier/Orin)
- **Resolution**: 1920x1080 @ 30 FPS
- **CPU Usage**: 20-40%
- **Memory**: ~600-1000 MB
- **Latency**: Similar to above

## Dependencies

### System Dependencies
- JetPack SDK (4.6+ or 5.0+)
- Python 3.6+
- OpenCV with CUDA
- GStreamer
- V4L2 utilities

### Python Dependencies
- opencv-python
- livekit
- flask, flask-socketio
- pyserial, pymavlink
- psutil, pyyaml
- (See requirements.txt for complete list)

## Network Requirements

### Ports Used
- **8080** (TCP): Web UI (configurable)
- **5600** (UDP): SIYI video transmission
- **37260** (UDP): SIYI control
- **7880** (WebSocket): LiveKit connection (default)

### Bandwidth Requirements
- **Camera capture**: N/A (local)
- **SIYI transmission**: ~2-5 Mbps
- **LiveKit streaming**: ~1-3 Mbps (configurable)
- **Web UI**: ~1-2 Mbps (local network)

## Security Considerations

1. **Web UI**: No authentication by default (add reverse proxy with auth)
2. **LiveKit**: Uses JWT tokens (secure)
3. **SIYI**: UDP protocol (no encryption)
4. **Network**: Recommend isolated network or firewall rules

## Extensibility

### Adding New Output Streams
1. Create new module in `src/`
2. Implement connection/send methods
3. Add to orchestrator's `_process_frame()`
4. Add configuration to `config.yaml`

### Adding Custom Telemetry
1. Add metric collection in `telemetry.py`
2. Update `_collect_telemetry()` method
3. Add to web UI visualization

### Customizing Web UI
1. Modify `web/templates/index.html`
2. Update styles in `web/static/style.css`
3. Add JavaScript logic in `web/static/app.js`

## Testing

### Unit Testing (Individual Components)
```bash
python3 src/camera_capture.py    # Test camera
python3 src/siyi_controller.py   # Test SIYI
python3 src/telemetry.py         # Test telemetry
python3 src/web_server.py        # Test web server
```

### Integration Testing
```bash
python3 main.py -v               # Run with verbose logging
```

### System Testing
```bash
./scripts/check_system.sh        # Check requirements
./scripts/test_camera.sh         # Test camera hardware
```

## Troubleshooting Tools

1. **System Check**: `./scripts/check_system.sh`
2. **Camera Test**: `./scripts/test_camera.sh`
3. **Logs**: `logs/stream.log`
4. **Web UI**: Real-time monitoring
5. **Jetson Stats**: `jtop` (if installed)

## Future Enhancements

### Potential Features
- [ ] H.264 hardware encoding for SIYI
- [ ] Recording to local storage
- [ ] Multi-camera support
- [ ] AI/ML inference integration
- [ ] Mobile app for monitoring
- [ ] RTSP streaming support
- [ ] Authentication for web UI
- [ ] Automatic camera detection
- [ ] Dynamic quality adjustment
- [ ] Cloud storage integration

## Known Limitations

1. **SIYI Protocol**: Basic implementation, may need updates for newer firmware
2. **LiveKit**: Requires external server setup
3. **Performance**: Limited by Jetson model and camera capabilities
4. **Security**: No built-in authentication/encryption
5. **Multi-camera**: Currently single camera only

## Support Matrix

### Tested Devices
- ✅ Jetson Nano (4GB)
- ✅ Jetson Xavier NX
- ⚠️ Jetson AGX Xavier (should work, not fully tested)
- ⚠️ Jetson Orin (should work, not fully tested)

### Tested Cameras
- ✅ Raspberry Pi Camera V2 (CSI)
- ✅ Logitech C920 (USB)
- ✅ Generic USB webcams
- ⚠️ Other CSI cameras (compatibility varies)

### Tested Configurations
- ✅ Camera + Web UI
- ✅ Camera + SIYI MK15
- ✅ Camera + LiveKit
- ✅ All components together

## License

[Specify your license]

## Credits

Developed for Jetson camera streaming applications with SIYI MK15 and LiveKit integration.

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-12  
**Status**: Production Ready
