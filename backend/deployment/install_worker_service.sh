#!/bin/bash

#############################################
# Install Harbor Worker as systemd Service
# Run this after setup_worker.sh completes
#############################################

set -e

echo "============================================"
echo "Installing Harbor Worker Service"
echo "============================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Get concurrency setting
CONCURRENCY="${1:-60}"
USERNAME="${2:-ubuntu}"
INSTALL_DIR="/home/$USERNAME/tbench-harbor-runner"

echo "Configuration:"
echo "  - User: $USERNAME"
echo "  - Install directory: $INSTALL_DIR"
echo "  - Concurrency: $CONCURRENCY"
echo ""

# Verify installation directory exists
if [ ! -d "$INSTALL_DIR/backend" ]; then
    echo "ERROR: Installation directory not found: $INSTALL_DIR/backend"
    echo "Please run setup_worker.sh first"
    exit 1
fi

# Verify .env file exists
if [ ! -f "$INSTALL_DIR/backend/.env" ]; then
    echo "ERROR: .env file not found"
    echo "Please run setup_worker.sh first"
    exit 1
fi

# Copy service file and replace placeholders
echo "Installing systemd service..."
SERVICE_FILE="/etc/systemd/system/harbor-worker.service"
cp "$INSTALL_DIR/backend/deployment/harbor-worker.service" "$SERVICE_FILE"

# Replace placeholders
sed -i "s|CONCURRENCY_PLACEHOLDER|$CONCURRENCY|g" "$SERVICE_FILE"
sed -i "s|/home/ubuntu|/home/$USERNAME|g" "$SERVICE_FILE"
sed -i "s|User=ubuntu|User=$USERNAME|g" "$SERVICE_FILE"
sed -i "s|Group=ubuntu|Group=$USERNAME|g" "$SERVICE_FILE"

# Reload systemd
systemctl daemon-reload

# Enable service (start on boot)
systemctl enable harbor-worker.service

echo ""
echo "✅ Harbor worker service installed successfully!"
echo ""
echo "Service management commands:"
echo "  Start:   sudo systemctl start harbor-worker"
echo "  Stop:    sudo systemctl stop harbor-worker"
echo "  Restart: sudo systemctl restart harbor-worker"
echo "  Status:  sudo systemctl status harbor-worker"
echo "  Logs:    sudo journalctl -u harbor-worker -f"
echo ""
read -p "Start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start harbor-worker
    echo ""
    echo "Service started. Checking status..."
    sleep 2
    systemctl status harbor-worker --no-pager
    echo ""
    echo "To view real-time logs:"
    echo "  sudo journalctl -u harbor-worker -f"
fi
