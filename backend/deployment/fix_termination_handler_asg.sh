#!/bin/bash
#
# Fix termination handler to detect ASG lifecycle termination
# Run this to update the termination handler to check both spot AND ASG termination
#

set -e

echo "Updating termination handler to detect ASG lifecycle state..."

cat > /usr/local/bin/harbor-termination-handler.py << 'EOF'
#!/usr/bin/env python3
"""
Harbor Worker Termination Handler

Polls for both:
1. Spot instance termination notices (EC2 metadata)
2. ASG lifecycle termination (Terminating:Wait state)

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
CELERY_SERVICE = "harbor-worker"
DRAIN_TIMEOUT = 2400  # 40 minutes for jobs to complete
AWS_REGION = "us-east-2"

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def get_imds_token():
    """Get IMDSv2 token"""
    try:
        req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method='PUT',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.read().decode().strip()
    except Exception as e:
        log(f"Warning: Could not get IMDSv2 token: {e}")
        return None

def get_metadata(path, token=None):
    """Get metadata with optional token"""
    url = f"http://169.254.169.254/latest/meta-data/{path}"
    headers = {}
    if token:
        headers['X-aws-ec2-metadata-token'] = token

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.read().decode().strip()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise

def check_spot_termination(token):
    """Check if spot instance is being terminated"""
    try:
        url = "http://169.254.169.254/latest/meta-data/spot/instance-action"
        headers = {}
        if token:
            headers['X-aws-ec2-metadata-token'] = token

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            action = data.get('action')
            time_str = data.get('time', 'unknown')
            log(f"Spot termination notice detected! Action: {action}, Time: {time_str}")
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return False
    except Exception:
        return False

def check_asg_termination(instance_id):
    """Check if ASG is terminating this instance"""
    if not instance_id:
        return None, None

    try:
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

                if 'Terminating:Wait' in lifecycle_state:
                    log(f"ASG termination detected! ASG={asg_name}, State={lifecycle_state}")

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
                        return asg_name, hook_name

        return None, None
    except Exception as e:
        log(f"Error checking ASG state: {e}")
        return None, None

def get_instance_id(token):
    """Get this instance's ID from metadata"""
    try:
        return get_metadata("instance-id", token)
    except Exception as e:
        log(f"Could not get instance ID: {e}")
        return None

def stop_celery_gracefully():
    """Stop Celery worker gracefully"""
    log("Stopping Celery worker gracefully...")

    try:
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

def complete_lifecycle_action(asg_name, hook_name, instance_id):
    """Signal AWS that we're ready for termination"""
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
    log(f"Polling every {POLL_INTERVAL} seconds for termination")
    log(f"Drain timeout: {DRAIN_TIMEOUT} seconds ({DRAIN_TIMEOUT//60} minutes)")

    # Get IMDSv2 token (valid for 6 hours)
    token = get_imds_token()
    if token:
        log("Using IMDSv2 (token-based authentication)")
    else:
        log("Using IMDSv1 (fallback)")

    instance_id = get_instance_id(token)
    log(f"Instance ID: {instance_id}")

    token_refresh_time = time.time()

    while True:
        try:
            # Refresh token every 5 hours
            if time.time() - token_refresh_time > 18000:
                token = get_imds_token()
                token_refresh_time = time.time()

            # Check for spot termination
            spot_terminating = check_spot_termination(token)

            # Check for ASG termination
            asg_name, hook_name = check_asg_termination(instance_id)
            asg_terminating = (asg_name is not None)

            if spot_terminating or asg_terminating:
                log("=" * 60)
                log("TERMINATION DETECTED - Beginning graceful shutdown")
                log("=" * 60)

                # Stop Celery gracefully
                success = stop_celery_gracefully()

                if success:
                    log("All jobs completed successfully")
                else:
                    log("Some jobs may not have completed")

                # Signal AWS if ASG termination with lifecycle hook
                if asg_name and hook_name:
                    complete_lifecycle_action(asg_name, hook_name, instance_id)
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

# Restart the service
sudo systemctl restart harbor-termination-handler.service

echo "✓ Termination handler updated and restarted"
echo ""
echo "Check logs:"
echo "  tail -f /var/log/harbor-termination-handler.log"
echo ""
echo "The handler now checks BOTH:"
echo "  1. Spot instance termination (EC2 metadata)"
echo "  2. ASG lifecycle termination (Terminating:Wait state)"
