#!/bin/bash

# Startup script for Jetson Camera Stream Application

echo "Starting Jetson Camera Stream with SIYI MK15..."

# Check if running on Jetson
if [ -f /etc/nv_tegra_release ]; then
    echo "Jetson device detected"
    # Set Jetson performance mode (optional)
    # sudo jetson_clocks
else
    echo "Warning: Not running on Jetson device"
fi

# Create logs directory
mkdir -p logs

# Check Python version
python3 --version

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check configuration
if [ ! -f "config.yaml" ]; then
    echo "Warning: config.yaml not found. Please create it from config.yaml.example"
    exit 1
fi

# Start the application
echo "Starting application..."
python3 src/main.py
