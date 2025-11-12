# Jetson Camera Streaming with SIYI MK15 & LiveKit

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Jetson-green.svg)

A comprehensive solution for streaming camera feeds from NVIDIA Jetson devices using SIYI MK15 wireless transmitter and LiveKit cloud streaming, with real-time telemetry monitoring and a beautiful web UI.

## ✨ Features

- 🎥 **Hardware-Accelerated Camera Capture** - GStreamer-based capture for CSI and USB cameras
- 📡 **SIYI MK15 Integration** - Wireless video transmission to handheld ground station
- ☁️ **LiveKit Streaming** - Cloud-based streaming for remote access
- 📊 **Real-Time Telemetry** - CPU, GPU, memory, temperature, and network monitoring
- 🌐 **Modern Web UI** - Beautiful, responsive interface for monitoring
- 🔧 **Highly Configurable** - YAML-based configuration for all components

## 🚀 Quick Start

```bash
# Clone repository
git clone <repo-url>
cd data-over-remote-controller

# Run automated setup
./setup.sh

# Configure (edit as needed)
nano config.yaml

# Activate environment and run
source venv/bin/activate
python3 main.py

# Access Web UI
http://localhost:8080
```

📖 **New to this?** Check out the [Quick Start Guide](QUICKSTART.md) for a 5-minute setup!

## 📸 Screenshots

### Web UI Dashboard
The web interface provides real-time monitoring of:
- Live video feed
- System telemetry (CPU, GPU, Memory, Temperature)
- Network statistics
- Connection status for SIYI and LiveKit

## 🎯 Use Cases

- **Drone Operations**: Stream FPV video via SIYI MK15 for real-time piloting
- **Remote Monitoring**: LiveKit streaming for cloud-based monitoring
- **Robotics**: Camera feed for remote robot operation
- **Security**: Multi-destination video streaming with telemetry
- **Research**: Real-time data collection and analysis

## 📁 Project Structure

```
data-over-remote-controller/
├── main.py                 # Main orchestrator
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── SETUP.md              # Detailed setup guide
├── src/
│   ├── camera_capture.py     # Jetson camera interface
│   ├── siyi_controller.py    # SIYI MK15 communication
│   ├── livekit_streamer.py   # LiveKit integration
│   ├── telemetry.py          # System telemetry
│   └── web_server.py         # Web UI server
└── web/
    ├── templates/
    │   └── index.html        # Web UI template
    └── static/
        ├── style.css         # Styles
        └── app.js            # Frontend logic
```

## 🔧 Configuration

Key configuration options in `config.yaml`:

```yaml
camera:
  device_id: 0
  width: 1920
  height: 1080
  fps: 30
  use_gstreamer: true

siyi:
  enabled: true
  transmitter_ip: "192.168.144.25"
  video_output_port: 5600

livekit:
  enabled: true
  url: "ws://localhost:7880"
  room_name: "jetson-camera-stream"

telemetry:
  enabled: true
  rate_hz: 5

web_ui:
  enabled: true
  host: "0.0.0.0"
  port: 8080
```

## 📚 Documentation

- **[SETUP.md](SETUP.md)** - Complete installation and configuration guide
- **[config.yaml](config.yaml)** - Configuration reference
- **Component Docs**:
  - Camera Capture: `src/camera_capture.py`
  - SIYI Controller: `src/siyi_controller.py`
  - LiveKit Streamer: `src/livekit_streamer.py`
  - Telemetry: `src/telemetry.py`

## 🛠️ Requirements

### Hardware
- NVIDIA Jetson (Nano, Xavier NX, AGX Xavier, Orin)
- Camera (CSI or USB)
- SIYI MK15 (optional)
- Network connection

### Software
- JetPack 4.6+ or 5.0+
- Python 3.6+
- See `requirements.txt` for Python packages

## 🎮 Usage

### Start Streaming
```bash
python3 main.py
```

### Test Individual Components
```bash
# Test camera
python3 src/camera_capture.py

# Test SIYI connection
python3 src/siyi_controller.py

# Test telemetry
python3 src/telemetry.py
```

### Access Web UI
```
http://<jetson-ip>:8080
```

## 🐛 Troubleshooting

Common issues and solutions:

1. **Camera not detected**: Check `/dev/video*` and verify connections
2. **Cannot connect to SIYI**: Verify network and IP address
3. **Poor performance**: Reduce resolution/FPS or enable GStreamer
4. **Web UI not accessible**: Check firewall settings

See [SETUP.md](SETUP.md) for detailed troubleshooting.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

[Your License Here]

## 🙏 Acknowledgments

- NVIDIA for Jetson platform
- SIYI for MK15 hardware
- LiveKit for streaming infrastructure
- Open source community

## 📞 Support

- 📖 Documentation: [SETUP.md](SETUP.md)
- 🐛 Issues: [GitHub Issues]
- 💬 Discussions: [GitHub Discussions]

---

Made with ❤️ for the Jetson community