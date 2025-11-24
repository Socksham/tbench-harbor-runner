#!/usr/bin/env python3
"""
Queue Depth Metric Publisher for Harbor Worker Auto-Scaling

This script:
1. Queries Redis for pending Celery tasks
2. Queries AWS ASG for running worker instances
3. Calculates queue depth per worker
4. Publishes metric to CloudWatch

Run every minute via cron for auto-scaling to work.
"""

import redis
import boto3
from datetime import datetime
import os
import sys

# Configuration - UPDATE THESE VALUES
REDIS_HOST = os.getenv('REDIS_HOST', 'h-redis.yx44yl.ng.0001.use2.cache.amazonaws.com')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
ASG_NAME = os.getenv('ASG_NAME', 'harbor-workers-asg')  # UPDATE THIS
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')  # UPDATE THIS
CLOUDWATCH_NAMESPACE = 'Harbor/Workers'
CLOUDWATCH_METRIC_NAME = 'QueueDepthPerWorker'

def get_queue_length():
    """Get number of pending tasks in Celery queue"""
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            socket_connect_timeout=5
        )

        # Celery uses 'celery' as default queue name
        # Check if your setup uses a different name
        queue_length = r.llen('celery')

        print(f"[INFO] Redis queue length: {queue_length}")
        return queue_length

    except redis.RedisError as e:
        print(f"[ERROR] Redis connection failed: {e}", file=sys.stderr)
        sys.exit(1)

def get_worker_count():
    """Get number of InService instances in ASG"""
    try:
        asg_client = boto3.client('autoscaling', region_name=AWS_REGION)

        response = asg_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[ASG_NAME]
        )

        if not response['AutoScalingGroups']:
            print(f"[ERROR] ASG '{ASG_NAME}' not found", file=sys.stderr)
            sys.exit(1)

        asg = response['AutoScalingGroups'][0]

        # Count instances that are InService
        in_service_count = sum(
            1 for instance in asg['Instances']
            if instance['LifecycleState'] == 'InService' and
               instance['HealthStatus'] == 'Healthy'
        )

        print(f"[INFO] InService workers: {in_service_count}")
        print(f"[INFO] Total instances: {len(asg['Instances'])}")
        print(f"[INFO] Desired capacity: {asg['DesiredCapacity']}")

        return in_service_count

    except boto3.exceptions.Boto3Error as e:
        print(f"[ERROR] AWS API call failed: {e}", file=sys.stderr)
        sys.exit(1)

def publish_metric(metric_value):
    """Publish metric to CloudWatch"""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name=AWS_REGION)

        cloudwatch.put_metric_data(
            Namespace=CLOUDWATCH_NAMESPACE,
            MetricData=[
                {
                    'MetricName': CLOUDWATCH_METRIC_NAME,
                    'Value': metric_value,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow(),
                    'Dimensions': [
                        {
                            'Name': 'AutoScalingGroupName',
                            'Value': ASG_NAME
                        }
                    ]
                }
            ]
        )

        print(f"[SUCCESS] Published metric: {metric_value} to CloudWatch")
        return True

    except boto3.exceptions.Boto3Error as e:
        print(f"[ERROR] CloudWatch publish failed: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """Main execution"""
    print(f"[INFO] Starting metric publisher at {datetime.now()}")
    print(f"[INFO] ASG: {ASG_NAME}")
    print(f"[INFO] Redis: {REDIS_HOST}:{REDIS_PORT}")

    # Get queue length
    queue_length = get_queue_length()

    # Get worker count
    worker_count = get_worker_count()

    # Calculate metric
    if worker_count == 0:
        # No workers available - metric = full queue length
        metric_value = queue_length
        print(f"[WARNING] No workers available! Queue length: {queue_length}")
    else:
        # Normal calculation
        metric_value = queue_length / worker_count
        print(f"[INFO] Calculated metric: {queue_length} / {worker_count} = {metric_value:.2f}")

    # Publish to CloudWatch
    publish_metric(metric_value)

    print(f"[INFO] Metric publisher completed successfully")
    print("-" * 60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
