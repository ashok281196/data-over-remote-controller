#!/bin/bash
# Check system requirements and configuration

echo "=========================================="
echo "System Check"
echo "=========================================="
echo ""

# Check Jetson info
echo "📊 System Information:"
if [ -f /etc/nv_tegra_release ]; then
    cat /etc/nv_tegra_release
    echo ""
else
    echo "⚠️  Not running on Jetson device"
    echo ""
fi

# Check Python version
echo "🐍 Python Version:"
python3 --version
echo ""

# Check if virtual environment exists
echo "🔧 Virtual Environment:"
if [ -d venv ]; then
    echo "✓ Virtual environment exists"
else
    echo "✗ Virtual environment not found (run setup.sh)"
fi
echo ""

# Check camera
echo "📹 Camera Devices:"
ls -l /dev/video* 2>/dev/null || echo "✗ No camera devices found"
echo ""

# Check network
echo "🌐 Network Interfaces:"
ip addr show | grep "inet " | awk '{print $2}' | grep -v "127.0.0.1"
echo ""

# Check disk space
echo "💾 Disk Space:"
df -h / | tail -n 1
echo ""

# Check memory
echo "🧠 Memory:"
free -h | grep Mem
echo ""

# Check CUDA
echo "🎮 CUDA:"
if command -v nvcc &> /dev/null; then
    nvcc --version | grep "release"
else
    echo "✗ CUDA not found"
fi
echo ""

# Check GStreamer
echo "🎬 GStreamer:"
if command -v gst-launch-1.0 &> /dev/null; then
    gst-launch-1.0 --version | head -n 1
else
    echo "✗ GStreamer not found"
fi
echo ""

# Check configuration files
echo "📝 Configuration Files:"
if [ -f config.yaml ]; then
    echo "✓ config.yaml exists"
else
    echo "✗ config.yaml not found"
fi

if [ -f .env ]; then
    echo "✓ .env exists"
else
    echo "✗ .env not found (copy from .env.example)"
fi
echo ""

echo "=========================================="
echo "System check complete!"
echo "=========================================="
