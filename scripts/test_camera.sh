#!/bin/bash
# Test camera functionality

echo "=========================================="
echo "Camera Test Script"
echo "=========================================="
echo ""

# List video devices
echo "📹 Video Devices:"
ls -l /dev/video* 2>/dev/null || echo "No video devices found!"
echo ""

# Get device info
echo "📋 Device Information:"
v4l2-ctl --list-devices 2>/dev/null || echo "v4l2-ctl not available"
echo ""

# Test CSI camera with GStreamer
echo "Testing CSI camera..."
read -p "Test CSI camera? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Opening CSI camera preview (Press Ctrl+C to stop)..."
    gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! \
        'video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1' ! \
        nvvidconv ! nvoverlaysink
fi

echo ""

# Test USB camera with GStreamer
echo "Testing USB camera..."
read -p "Test USB camera on /dev/video0? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Opening USB camera preview (Press Ctrl+C to stop)..."
    gst-launch-1.0 v4l2src device=/dev/video0 ! \
        'video/x-raw, width=1280, height=720' ! \
        xvimagesink
fi

echo ""
echo "Camera test complete!"
