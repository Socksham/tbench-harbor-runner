#!/bin/bash
#
# Graceful Shutdown Setup for Harbor Workers
#
# This script installs a termination handler that:
# 1. Detects when AWS is terminating the instance
# 2. Stops Celery from accepting new tasks
# 3. Waits for current Harbor jobs to finish (up to 40 minutes)
# 4. Signals AWS that termination can proceed
#
# Run this on your worker instance before creating the AMI
#

set -e

echo "=========================================="
echo "Harbor Worker Graceful Shutdown Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root (use sudo)"
    exit 1
fi

# Step 1: Create the termination detector script
echo "[1/4] Creating termination detector script..."

cat > /usr/local/bin/harbor-termination-handler.py << 'EOF'
#!/usr/bin/env python3
"""
Harbor Worker Termination Handler

Polls EC2 metadata for termination notice.
When detected, gracefully shuts down Celery worker.
"""

import time
import subprocess
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime

# Configuration
POLL_INTERVAL = 30  # Check every 30 seconds
METADATA_URL = "http://169.254.169.254/latest/meta-data/spot/instance-action"
CELERY_SERVICE = "harbor-worker"
DRAIN_TIMEOUT = 2400  # 40 minutes for jobs to complete
AWS_REGION = "us-east-2"

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def check_termination_notice():
    """Check if AWS is terminating this instance"""
    try:
        req = urllib.request.Request(METADATA_URL, headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            action = data.get('action')
            time_str = data.get('time', 'unknown')
            log(f"Termination notice detected! Action: {action}, Time: {time_str}")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # No termination notice (expected most of the time)
            return False
        else:
            log(f"Error checking metadata: {e}")
            return False
    except Exception as e:
        log(f"Unexpected error: {e}")
        return False

def get_instance_id():
    """Get this instance's ID from metadata"""
    try:
        req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.read().decode().strip()
    except Exception as e:
        log(f"Could not get instance ID: {e}")
        return None

def get_lifecycle_hook_name():
    """Get lifecycle hook name (if in terminating:wait state)"""
    instance_id = get_instance_id()
    if not instance_id:
        return None, None

    try:
        # Query ASG to find this instance's lifecycle state
        result = subprocess.run([
            'aws', 'autoscaling', 'describe-auto-scaling-instances',
            '--instance-ids', instance_id,
            '--region', AWS_REGION,
            '--query', 'AutoScalingInstances[0].[AutoScalingGroupName,LifecycleState]',
            '--output', 'text'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            output = result.stdout.strip().split('\t')
            if len(output) == 2:
                asg_name, lifecycle_state = output
                log(f"Instance state: ASG={asg_name}, LifecycleState={lifecycle_state}")

                if 'Terminating:Wait' in lifecycle_state:
                    # Get the lifecycle hook name
                    hooks_result = subprocess.run([
                        'aws', 'autoscaling', 'describe-lifecycle-hooks',
                        '--auto-scaling-group-name', asg_name,
                        '--region', AWS_REGION,
                        '--query', 'LifecycleHooks[?LifecycleTransition==`autoscaling:EC2_INSTANCE_TERMINATING`].LifecycleHookName',
                        '--output', 'text'
                    ], capture_output=True, text=True, timeout=10)

                    if hooks_result.returncode == 0:
                        hook_name = hooks_result.stdout.strip()
                        log(f"Found lifecycle hook: {hook_name}")
                        return asg_name, hook_name

        return None, None
    except Exception as e:
        log(f"Error getting lifecycle info: {e}")
        return None, None

def stop_celery_gracefully():
    """Stop Celery worker gracefully"""
    log("Stopping Celery worker gracefully...")

    try:
        # Use systemd to stop the service (triggers SIGTERM)
        subprocess.run(['systemctl', 'stop', CELERY_SERVICE], check=True, timeout=DRAIN_TIMEOUT)
        log("Celery stopped successfully")
        return True
    except subprocess.TimeoutExpired:
        log("WARNING: Celery did not stop within timeout, forcing stop")
        subprocess.run(['systemctl', 'kill', CELERY_SERVICE], check=False)
        return False
    except Exception as e:
        log(f"Error stopping Celery: {e}")
        return False

def complete_lifecycle_action(asg_name, hook_name):
    """Signal AWS that we're ready for termination"""
    instance_id = get_instance_id()
    if not instance_id or not asg_name or not hook_name:
        log("Cannot complete lifecycle action - missing info")
        return False

    log(f"Signaling lifecycle completion to AWS...")

    try:
        subprocess.run([
            'aws', 'autoscaling', 'complete-lifecycle-action',
            '--lifecycle-action-result', 'CONTINUE',
            '--lifecycle-hook-name', hook_name,
            '--auto-scaling-group-name', asg_name,
            '--instance-id', instance_id,
            '--region', AWS_REGION
        ], check=True, timeout=10)

        log("Successfully signaled AWS - termination can proceed")
        return True
    except Exception as e:
        log(f"Error completing lifecycle action: {e}")
        return False

def main():
    """Main loop"""
    log("Harbor Termination Handler started")
    log(f"Polling every {POLL_INTERVAL} seconds for termination notice")
    log(f"Drain timeout: {DRAIN_TIMEOUT} seconds ({DRAIN_TIMEOUT//60} minutes)")

    instance_id = get_instance_id()
    log(f"Instance ID: {instance_id}")

    while True:
        try:
            # Check for termination notice
            if check_termination_notice():
                log("=" * 60)
                log("TERMINATION DETECTED - Beginning graceful shutdown")
                log("=" * 60)

                # Get lifecycle hook info
                asg_name, hook_name = get_lifecycle_hook_name()

                # Stop Celery gracefully
                success = stop_celery_gracefully()

                if success:
                    log("All jobs completed successfully")
                else:
                    log("Some jobs may not have completed")

                # Signal AWS we're ready
                if asg_name and hook_name:
                    complete_lifecycle_action(asg_name, hook_name)
                else:
                    log("No lifecycle hook found, instance will terminate on timeout")

                log("Graceful shutdown complete - exiting")
                sys.exit(0)

            # Sleep until next check
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("Interrupted by user - exiting")
            sys.exit(0)
        except Exception as e:
            log(f"Unexpected error in main loop: {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
EOF

chmod +x /usr/local/bin/harbor-termination-handler.py
echo "✓ Termination handler created"

# Step 2: Create systemd service for termination handler
echo ""
echo "[2/4] Creating systemd service..."

cat > /etc/systemd/system/harbor-termination-handler.service << 'EOF'
[Unit]
Description=Harbor Worker Graceful Termination Handler
After=network.target harbor-worker.service
Wants=harbor-worker.service

[Service]
Type=simple
ExecStart=/usr/local/bin/harbor-termination-handler.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/harbor-termination-handler.log
StandardError=append:/var/log/harbor-termination-handler.log

# Run as ubuntu user
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Systemd service created"

# Step 3: Update Celery service for graceful shutdown
echo ""
echo "[3/4] Updating Celery worker service..."

# Backup existing service if it exists
if [ -f /etc/systemd/system/harbor-worker.service ]; then
    cp /etc/systemd/system/harbor-worker.service /etc/systemd/system/harbor-worker.service.backup
    echo "✓ Backed up existing service"
fi

cat > /etc/systemd/system/harbor-worker.service << 'EOF'
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

# Start Celery worker
ExecStart=/home/ubuntu/tbench-harbor-runner/backend/venv/bin/celery -A workers.harbor_worker worker \
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

echo "✓ Celery service updated with graceful shutdown (40 min timeout)"

# Step 4: Enable and start services
echo ""
echo "[4/4] Enabling services..."

# Create log files
touch /var/log/harbor-termination-handler.log
touch /var/log/harbor-worker.log
chown ubuntu:ubuntu /var/log/harbor-termination-handler.log
chown ubuntu:ubuntu /var/log/harbor-worker.log

# Reload systemd
systemctl daemon-reload

# Enable services (start on boot)
systemctl enable harbor-termination-handler.service
systemctl enable harbor-worker.service

# Start termination handler (Celery might already be running)
systemctl start harbor-termination-handler.service

echo "✓ Services enabled"

echo ""
echo "=========================================="
echo "✓ Graceful Shutdown Setup Complete!"
echo "=========================================="
echo ""
echo "What was installed:"
echo "  - Termination detector: /usr/local/bin/harbor-termination-handler.py"
echo "  - Systemd service: harbor-termination-handler.service"
echo "  - Updated Celery service: harbor-worker.service (40 min timeout)"
echo ""
echo "Services status:"
systemctl status harbor-termination-handler.service --no-pager -l || true
echo ""
echo "Logs:"
echo "  - Termination handler: /var/log/harbor-termination-handler.log"
echo "  - Celery worker: /var/log/harbor-worker.log"
echo ""
echo "Monitor termination handler:"
echo "  tail -f /var/log/harbor-termination-handler.log"
echo ""
echo "Next steps:"
echo "  1. Check logs to verify it's running"
echo "  2. Test by manually decreasing ASG desired capacity"
echo "  3. Create new AMI from this instance"
echo "  4. Update launch template to use new AMI"
echo ""
