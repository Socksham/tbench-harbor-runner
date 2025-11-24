#!/bin/bash
#
# Fix Harbor CLI PATH in systemd service
# Run this to update the harbor-worker service to include Harbor CLI in PATH
#

set -e

echo "Fixing Harbor CLI PATH in harbor-worker.service..."

# Update the service file to include /home/ubuntu/.local/bin in PATH
sudo tee /etc/systemd/system/harbor-worker.service > /dev/null << 'EOF'
[Unit]
Description=Harbor Celery Worker
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/tbench-harbor-runner/backend

# Load environment variables
EnvironmentFile=/home/ubuntu/tbench-harbor-runner/backend/.env

# Add Harbor CLI to PATH
Environment="PATH=/home/ubuntu/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Start Celery worker
ExecStart=/home/ubuntu/venv/bin/celery -A workers.harbor_worker worker \
    --loglevel=info \
    --concurrency=60 \
    --max-tasks-per-child=50 \
    --hostname=worker-$(hostname)@%%h

# Graceful shutdown handling
ExecStop=/bin/kill -TERM $MAINPID
TimeoutStopSec=2400
KillMode=mixed
KillSignal=SIGTERM

# Restart policy
Restart=on-failure
RestartSec=10

# Logging
StandardOutput=append:/var/log/harbor-worker.log
StandardError=append:/var/log/harbor-worker.log

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service file updated"

# Reload systemd and restart service
sudo systemctl daemon-reload
sudo systemctl restart harbor-worker.service

echo "✓ Service restarted"
echo ""
echo "Verify it's working:"
echo "  systemctl status harbor-worker.service"
echo "  ps aux | grep celery"
