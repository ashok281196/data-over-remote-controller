# Jetson Camera Streaming with SIYI MK15 and LiveKit

Complete setup guide for streaming camera feeds from Jetson devices using SIYI MK15 transmitter and LiveKit cloud streaming.

## 📋 Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [Software Requirements](#software-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This system enables:
- **Camera Capture**: Hardware-accelerated video capture from Jetson cameras (CSI or USB)
- **SIYI MK15 Streaming**: Video transmission to SIYI MK15 handheld ground station
- **LiveKit Streaming**: Cloud streaming for remote monitoring
- **Telemetry**: Real-time system metrics (CPU, GPU, memory, temperature, network)
- **Web UI**: Beautiful web interface for monitoring streams and telemetry

## 🔧 Hardware Requirements

### Required
- **Jetson Device**: Nano, Xavier NX, AGX Xavier, or Orin series
- **Camera**: 
  - CSI camera (e.g., Raspberry Pi Camera V2) OR
  - USB camera (e.g., Logitech C920)
- **Network Connection**: Ethernet or WiFi

### Optional
- **SIYI MK15**: Handheld ground station for wireless video transmission
- **Power Supply**: Adequate power for Jetson and peripherals

## 💻 Software Requirements

- **JetPack**: 4.6+ (for Jetson Nano/Xavier) or 5.0+ (for Orin)
- **Python**: 3.6+
- **CUDA**: Included with JetPack
- **GStreamer**: Included with JetPack

## 📦 Installation

### Step 1: System Preparation

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    libopencv-dev \
    v4l-utils \
    git

# Install GStreamer plugins (if not already installed)
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad
```

### Step 2: Clone Repository

```bash
cd ~
git clone <your-repo-url>
cd data-over-remote-controller
```

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 4: Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# For Jetson-specific optimizations, you may need:
pip install jetson-stats  # For GPU monitoring
```

### Step 5: Verify Camera

```bash
# List available video devices
ls -l /dev/video*

# Test camera with v4l2
v4l2-ctl --list-devices

# For CSI camera, test with GStreamer
gst-launch-1.0 nvarguscamerasrc ! nvoverlaysink

# For USB camera, test with GStreamer
gst-launch-1.0 v4l2src device=/dev/video0 ! xvimagesink
```

## ⚙️ Configuration

### Step 1: Copy Environment Template

```bash
cp .env.example .env
```

### Step 2: Edit Configuration

Edit `config.yaml` to match your setup:

```yaml
# Camera Settings
camera:
  device_id: 0  # 0 for CSI camera or /dev/video0 for USB
  width: 1920
  height: 1080
  fps: 30
  use_gstreamer: true  # true for CSI camera, false for USB
```

### Step 3: Configure SIYI MK15 (if using)

1. **Connect SIYI MK15** to the same network as your Jetson
2. **Find SIYI IP address** (default: 192.168.144.25)
3. **Update config.yaml**:

```yaml
siyi:
  enabled: true
  transmitter_ip: "192.168.144.25"  # Update with your SIYI IP
  video_output_port: 5600
```

### Step 4: Configure LiveKit (if using)

1. **Sign up for LiveKit Cloud** or set up self-hosted LiveKit server
2. **Get API credentials** from LiveKit dashboard
3. **Update .env file**:

```bash
LIVEKIT_URL=wss://your-livekit-server.com
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
LIVEKIT_ROOM_NAME=jetson-stream
```

Or disable in `config.yaml`:

```yaml
livekit:
  enabled: false  # Set to false if not using LiveKit
```

## 🚀 Usage

### Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default config
python3 main.py

# Run with custom config
python3 main.py -c my_config.yaml

# Run with verbose logging
python3 main.py -v
```

### Access Web UI

Open your browser and navigate to:
```
http://<jetson-ip>:8080
```

Or if running locally:
```
http://localhost:8080
```

### Test Individual Components

```bash
# Test camera only
cd src
python3 camera_capture.py

# Test SIYI connection
python3 siyi_controller.py

# Test telemetry collection
python3 telemetry.py

# Test web server
python3 web_server.py
```

## 🎮 Operation

### Starting the System

1. **Power on Jetson** and wait for boot
2. **Connect SIYI MK15** (if using) and verify network connection
3. **Run the main script**:
   ```bash
   python3 main.py
   ```
4. **Open Web UI** in browser
5. **Verify streams** are active

### Monitoring

- **Web UI**: Real-time video and telemetry at `http://<jetson-ip>:8080`
- **Console Logs**: Watch terminal for status messages
- **Log File**: Check `logs/stream.log` for detailed logs

### Stopping the System

Press `Ctrl+C` in the terminal to gracefully shutdown all components.

## 🔍 Troubleshooting

### Camera Issues

**Problem**: Camera not detected
```bash
# Check camera connections
ls -l /dev/video*

# Verify camera with v4l2
v4l2-ctl --list-devices
v4l2-ctl -d /dev/video0 --list-formats-ext

# For CSI camera, check with nvgstcapture
nvgstcapture-1.0
```

**Problem**: Low FPS or poor quality
- Reduce resolution in `config.yaml`
- Enable hardware acceleration: `use_gstreamer: true`
- Check CPU/GPU usage in web UI

### SIYI MK15 Issues

**Problem**: Cannot connect to SIYI
```bash
# Check network connectivity
ping 192.168.144.25

# Verify SIYI is on same network
ip addr show

# Check firewall rules
sudo ufw status
```

**Problem**: No video on SIYI display
- Verify UDP port 5600 is not blocked
- Check SIYI firmware version
- Ensure SIYI is in correct input mode

### LiveKit Issues

**Problem**: Cannot connect to LiveKit
- Verify API credentials in `.env`
- Check internet connectivity
- Test LiveKit URL in browser
- Check firewall allows WebSocket connections

**Problem**: Poor streaming quality
- Adjust bitrate in `config.yaml`:
  ```yaml
  livekit:
    video_bitrate: 1000000  # Lower bitrate (1 Mbps)
  ```
- Check network bandwidth

### Performance Issues

**Problem**: High CPU usage
```bash
# Monitor system resources
jtop  # If jetson-stats installed
htop  # Alternative

# Reduce camera resolution
# Disable unused features in config.yaml
```

**Problem**: System overheating
- Check cooling
- Monitor temperature in web UI
- Reduce workload (lower FPS, resolution)
- Add `nvpmodel` power mode adjustment:
  ```bash
  sudo nvpmodel -m 0  # Max performance
  sudo nvpmodel -m 1  # Balanced
  ```

### Web UI Issues

**Problem**: Cannot access web UI
```bash
# Check if server is running
netstat -tuln | grep 8080

# Try different port
python3 main.py  # Edit config.yaml port: 8081

# Check firewall
sudo ufw allow 8080
```

**Problem**: Video feed not displaying
- Check browser console for errors
- Verify camera is working: `python3 src/camera_capture.py`
- Clear browser cache

## 📊 Performance Tuning

### For Maximum Performance

1. **Enable MAXN mode**:
   ```bash
   sudo nvpmodel -m 0
   sudo jetson_clocks
   ```

2. **Use hardware encoding**:
   ```yaml
   camera:
     use_gstreamer: true
   ```

3. **Optimize resolution/FPS**:
   ```yaml
   camera:
     width: 1280
     height: 720
     fps: 30
   ```

### For Power Efficiency

1. **Enable power-save mode**:
   ```bash
   sudo nvpmodel -m 1
   ```

2. **Lower resolution/FPS**:
   ```yaml
   camera:
     width: 640
     height: 480
     fps: 15
   ```

3. **Disable unused features**:
   ```yaml
   livekit:
     enabled: false
   ```

## 🔒 Security Considerations

1. **Change default credentials** in LiveKit
2. **Use firewall** to restrict access:
   ```bash
   sudo ufw enable
   sudo ufw allow 8080  # Web UI
   sudo ufw allow 5600/udp  # SIYI video
   ```
3. **Use HTTPS** for web UI in production
4. **Keep system updated**:
   ```bash
   sudo apt update && sudo apt upgrade
   ```

## 📝 Additional Resources

- [SIYI SDK Documentation](https://siyi.biz/)
- [LiveKit Documentation](https://docs.livekit.io/)
- [Jetson GStreamer Guide](https://developer.nvidia.com/embedded/jetson-gstreamer-guide)
- [OpenCV on Jetson](https://docs.opencv.org/)

## 🆘 Support

For issues and questions:
1. Check this documentation
2. Review logs in `logs/stream.log`
3. Test individual components
4. Check hardware connections
5. Verify network connectivity

## 📄 License

[Your License Here]

## 🤝 Contributing

Contributions welcome! Please submit issues and pull requests.
