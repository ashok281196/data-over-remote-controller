# 🚀 Quick Start Guide

Get up and running in 5 minutes!

## Prerequisites

- NVIDIA Jetson device (Nano, Xavier, or Orin)
- Camera connected (CSI or USB)
- Internet connection (for LiveKit, optional)

## Installation

### 1. Clone and Setup

```bash
# Clone repository
cd ~
git clone <your-repo-url>
cd data-over-remote-controller

# Run automated setup
./setup.sh
```

### 2. Configure

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (use nano or vi)
nano config.yaml
```

**Minimal configuration for local testing:**
```yaml
camera:
  device_id: 0
  width: 1280
  height: 720
  fps: 30
  use_gstreamer: false  # Set true for CSI camera

siyi:
  enabled: false  # Disable if no SIYI hardware

livekit:
  enabled: false  # Disable if no LiveKit server

web_ui:
  enabled: true
  port: 8080
```

### 3. Run

```bash
# Activate virtual environment
source venv/bin/activate

# Start streaming
python3 main.py
```

### 4. View

Open browser and go to:
```
http://localhost:8080
```

## Testing Individual Components

### Test Camera Only

```bash
source venv/bin/activate
cd src
python3 camera_capture.py
```

Press 'q' to quit the camera test window.

### Check System Status

```bash
./scripts/check_system.sh
```

### Test Camera with Script

```bash
./scripts/test_camera.sh
```

## Common Configurations

### USB Camera (Logitech, etc.)

```yaml
camera:
  device_id: 0
  use_gstreamer: false
  width: 1280
  height: 720
  fps: 30
```

### CSI Camera (Raspberry Pi Camera V2)

```yaml
camera:
  device_id: 0
  use_gstreamer: true
  width: 1920
  height: 1080
  fps: 30
```

### With SIYI MK15

```yaml
siyi:
  enabled: true
  transmitter_ip: "192.168.144.25"  # Your SIYI IP
  video_output_port: 5600
```

### With LiveKit

1. Sign up at [LiveKit Cloud](https://livekit.io)
2. Get your credentials
3. Update `.env`:

```bash
LIVEKIT_URL=wss://your-server.livekit.cloud
LIVEKIT_API_KEY=your-key
LIVEKIT_API_SECRET=your-secret
```

4. Enable in `config.yaml`:

```yaml
livekit:
  enabled: true
  room_name: "my-jetson-stream"
```

## Troubleshooting

### Camera not working?

```bash
# Check camera devices
ls -l /dev/video*

# Test camera
./scripts/test_camera.sh
```

### Port 8080 already in use?

Change port in `config.yaml`:
```yaml
web_ui:
  port: 8081  # Use different port
```

### Poor performance?

1. Lower resolution:
   ```yaml
   camera:
     width: 640
     height: 480
   ```

2. Enable hardware acceleration:
   ```yaml
   camera:
     use_gstreamer: true
   ```

3. Reduce FPS:
   ```yaml
   camera:
     fps: 15
   ```

## Next Steps

- Read [SETUP.md](SETUP.md) for detailed configuration
- Configure SIYI MK15 integration
- Set up LiveKit for remote streaming
- Customize web UI appearance
- Add custom telemetry metrics

## Getting Help

- 📖 Full Documentation: [SETUP.md](SETUP.md)
- 🐛 Issues: Create a GitHub issue
- 💬 Questions: Check GitHub Discussions

## Quick Commands

```bash
# Start streaming
python3 main.py

# Start with verbose logging
python3 main.py -v

# Use custom config
python3 main.py -c my_config.yaml

# Check system
./scripts/check_system.sh

# Test camera
./scripts/test_camera.sh
```

---

**Happy Streaming! 🎥**
