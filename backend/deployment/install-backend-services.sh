#!/bin/bash
#
# Install systemd services for Harbor Runner backend and frontend
#

set -e

echo "Installing Harbor Runner services..."

# Stop existing manual processes
echo "Stopping existing processes..."
pkill -f "uvicorn app.main:app" || true
pkill -f "npm run start" || true

# Copy service files
echo "Installing service files..."
sudo cp harbor-backend.service /etc/systemd/system/
sudo cp harbor-frontend.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable services (start on boot)
echo "Enabling services..."
sudo systemctl enable harbor-backend.service
sudo systemctl enable harbor-frontend.service

# Start services
echo "Starting services..."
sudo systemctl start harbor-backend.service
sudo systemctl start harbor-frontend.service

# Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status harbor-backend.service --no-pager
echo ""
sudo systemctl status harbor-frontend.service --no-pager

echo ""
echo "✓ Installation complete!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status harbor-backend"
echo "  sudo systemctl status harbor-frontend"
echo "  sudo systemctl restart harbor-backend"
echo "  sudo systemctl restart harbor-frontend"
echo "  sudo journalctl -u harbor-backend -f"
echo "  sudo journalctl -u harbor-frontend -f"
