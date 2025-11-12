# Jetson Camera Stream with SIYI MK15 Transmitter

A comprehensive solution for streaming video from a Jetson device camera through SIYI MK15 transmitter and LiveKit, with real-time telemetry monitoring and web UI.

## Features

- 📹 **Camera Capture**: Supports both CSI cameras (nvarguscamerasrc) and USB cameras (v4l2src) on Jetson devices
- 📡 **SIYI MK15 Integration**: Full integration with SIYI MK15 video transmitter for remote video transmission
- 🌐 **LiveKit Streaming**: Real-time video and telemetry streaming via LiveKit
- 📊 **Telemetry Monitoring**: GPS, attitude, battery, and system statistics
- 🖥️ **Web UI**: Beautiful, responsive web interface for monitoring streams and telemetry data
- ⚡ **Real-time Updates**: WebSocket-based real-time telemetry updates

## Prerequisites

- NVIDIA Jetson device (Nano, Xavier, Orin, etc.)
- Python 3.8 or higher
- Camera connected to Jetson (CSI or USB)
- SIYI MK15 transmitter connected via serial port
- LiveKit server (self-hosted or cloud)
- GStreamer (usually pre-installed on Jetson)

## Installation

### 1. Clone and Setup

```bash
cd /workspace
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure the Application

Copy the example environment file and edit it:

```bash
cp .env.example .env
nano .env
```

Edit `config.yaml` with your specific settings:

```yaml
camera:
  device_id: 0  # Camera device ID
  width: 1920
  height: 1080
  fps: 30
  source_type: "nvarguscamerasrc"  # or "v4l2src" for USB

livekit:
  url: "wss://your-livekit-server.com"
  api_key: "your-api-key"
  api_secret: "your-api-secret"
  room_name: "jetson-camera-stream"

siyi_mk15:
  serial_port: "/dev/ttyUSB0"  # Adjust based on your connection
  baudrate: 115200
  enable_video_transmission: true
  video_quality: "high"
```

### 4. Find Your Camera Device

For CSI cameras:
```bash
ls /dev/video*
```

For USB cameras:
```bash
v4l2-ctl --list-devices
```

### 5. Find SIYI MK15 Serial Port

```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Or check dmesg after connecting:
dmesg | tail
```

## Usage

### Start the Application

```bash
python3 src/main.py
```

The application will:
1. Initialize camera capture
2. Connect to SIYI MK15 transmitter
3. Connect to LiveKit server
4. Start telemetry collection
5. Launch web UI on `http://localhost:8080`

### Access Web UI

Open your browser and navigate to:
```
http://<jetson-ip>:8080
```

The web UI provides:
- Real-time video stream
- Live telemetry data (GPS, attitude, system stats)
- Connection status indicators
- Control buttons

### Stop the Application

Press `Ctrl+C` to gracefully shutdown all components.

## Project Structure

```
/workspace
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main application orchestrator
│   ├── camera_capture.py       # Camera capture module
│   ├── siyi_mk15.py           # SIYI MK15 transmitter integration
│   ├── livekit_streamer.py    # LiveKit streaming module
│   ├── telemetry_handler.py   # Telemetry data handler
│   └── web_ui.py              # Web UI server
├── config.yaml                # Configuration file
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables example
└── README.md                 # This file
```

## Configuration Details

### Camera Settings

- **device_id**: Camera device number (usually 0)
- **width/height**: Video resolution
- **fps**: Frames per second
- **source_type**: 
  - `"nvarguscamerasrc"` for CSI cameras (Jetson native)
  - `"v4l2src"` for USB cameras

### SIYI MK15 Settings

- **serial_port**: Serial port path (e.g., `/dev/ttyUSB0`)
- **baudrate**: Communication baud rate (typically 115200)
- **video_quality**: `"high"`, `"medium"`, or `"low"`

### LiveKit Settings

- **url**: Your LiveKit server WebSocket URL
- **api_key**: LiveKit API key
- **api_secret**: LiveKit API secret
- **room_name**: Room name for streaming

### Telemetry Settings

- **update_rate**: Telemetry update frequency in Hz
- **include_gps**: Include GPS coordinates
- **include_attitude**: Include roll/pitch/yaw
- **include_battery**: Include battery information
- **include_system_stats**: Include CPU/memory/temperature

## Troubleshooting

### Camera Not Detected

1. Check camera connection:
   ```bash
   ls /dev/video*
   ```

2. Test camera with GStreamer:
   ```bash
   gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! nvvidconv ! 'video/x-raw,width=1920,height=1080' ! nvoverlaysink
   ```

### SIYI MK15 Connection Issues

1. Check serial port permissions:
   ```bash
   sudo chmod 666 /dev/ttyUSB0
   ```

2. Add user to dialout group:
   ```bash
   sudo usermod -a -G dialout $USER
   ```

3. Verify connection:
   ```bash
   sudo minicom -D /dev/ttyUSB0 -b 115200
   ```

### LiveKit Connection Failed

1. Verify LiveKit server is accessible
2. Check API credentials in `config.yaml`
3. Ensure network connectivity

### Performance Issues

1. Reduce video resolution in `config.yaml`
2. Lower FPS if needed
3. Check Jetson thermal throttling:
   ```bash
   sudo jetson_clocks
   ```

## SIYI MK15 Protocol Notes

The SIYI MK15 integration uses a custom protocol over serial communication. The implementation includes:

- Heartbeat mechanism for connection monitoring
- Video transmission control
- Telemetry data reception
- Command/response handling

**Note**: The telemetry parsing in `siyi_mk15.py` may need adjustment based on your specific SIYI MK15 firmware version and protocol. Refer to SIYI MK15 documentation for exact packet formats.

## Development

### Adding Custom Telemetry Sources

Edit `src/telemetry_handler.py` to add custom telemetry sources:

```python
def update_custom_source(self, data):
    self.current_telemetry.custom_field = data
```

### Extending Web UI

Modify `src/web_ui.py` to add new UI components or endpoints.

### Custom Camera Sources

Extend `src/camera_capture.py` to support additional camera types or configurations.

## License

This project is provided as-is for use with Jetson devices and SIYI MK15 transmitters.

## Support

For issues related to:
- **Jetson**: Check NVIDIA Jetson documentation
- **SIYI MK15**: Refer to SIYI MK15 user manual
- **LiveKit**: See LiveKit documentation
- **This Application**: Review logs in `logs/jetson_stream.log`

## Acknowledgments

- NVIDIA Jetson platform
- SIYI MK15 transmitter
- LiveKit for real-time streaming infrastructure
