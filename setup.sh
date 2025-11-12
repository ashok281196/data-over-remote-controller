#!/bin/bash
# Setup script for Jetson Camera Streaming System

set -e

echo "=========================================="
echo "Jetson Camera Streaming Setup"
echo "=========================================="
echo ""

# Check if running on Jetson
if [ ! -f /etc/nv_tegra_release ]; then
    echo "⚠️  Warning: This script is designed for Jetson devices"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-opencv \
    libopencv-dev \
    v4l-utils \
    git \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create logs directory
echo "📁 Creating directories..."
mkdir -p logs

# Copy environment template
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration"
else
    echo "✓ .env file already exists"
fi

# Test camera
echo ""
echo "=========================================="
echo "Testing Camera"
echo "=========================================="
echo ""

read -p "Would you like to test the camera? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Available video devices:"
    ls -l /dev/video* || echo "No video devices found"
    
    echo ""
    echo "Camera information:"
    v4l2-ctl --list-devices || echo "v4l2-ctl not available"
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config.yaml with your settings"
echo "2. Edit .env with your API keys (if using LiveKit)"
echo "3. Run: source venv/bin/activate"
echo "4. Run: python3 main.py"
echo "5. Open browser: http://localhost:8080"
echo ""
echo "For detailed instructions, see SETUP.md"
echo ""
