#!/bin/bash
# Install jetson-stats for enhanced GPU and system monitoring

echo "Installing jetson-stats..."

# Install jetson-stats
sudo pip3 install jetson-stats

echo ""
echo "jetson-stats installed successfully!"
echo ""
echo "Usage:"
echo "  - Run 'jtop' to monitor system"
echo "  - Run 'jetson_release' to show Jetson info"
echo ""
echo "Note: You may need to reboot for jtop to work properly"
