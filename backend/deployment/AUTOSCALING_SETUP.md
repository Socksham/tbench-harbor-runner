# Auto-Scaling Setup Guide

## Quick Start

On your backend EC2 instance:

```bash
cd ~/tbench-harbor-runner/backend/deployment
./setup_autoscaling_metric.sh
```

That's it! The script will:
- Install dependencies
- Configure the metric publisher
- Set up cron job to run every minute
- Test the setup

---

## What This Does

Creates a feedback loop for auto-scaling:

```
Every Minute:
  1. Check Redis queue length (pending Celery tasks)
  2. Count workers in ASG (InService instances)
  3. Calculate: queue_length / worker_count
  4. Publish to CloudWatch as "QueueDepthPerWorker"

Auto Scaling Group:
  - Monitors CloudWatch metric
  - Keeps metric close to target value (e.g., 60)
  - Adds workers when metric > target
  - Removes workers when metric < target
```

---

## Configuration

The setup script will ask you for:

1. **ASG Name**: Your Auto Scaling Group name (default: `harbor-workers-asg`)
2. **AWS Region**: Where your ASG is (default: `us-east-2`)

These are saved to: `/home/ubuntu/harbor-metric-publisher.env`

---

## Verify It's Working

### Step 1: Check the logs (after 1-2 minutes)

```bash
tail -f /var/log/harbor-metric-publisher.log
```

You should see output like:
```
[INFO] Starting metric publisher at 2025-11-24 10:15:00
[INFO] ASG: harbor-workers-asg
[INFO] Redis: h-redis.yx44yl.ng.0001.use2.cache.amazonaws.com:6379
[INFO] Redis queue length: 25
[INFO] InService workers: 5
[INFO] Total instances: 5
[INFO] Desired capacity: 5
[INFO] Calculated metric: 25 / 5 = 5.00
[SUCCESS] Published metric: 5.0 to CloudWatch
[INFO] Metric publisher completed successfully
```

### Step 2: Check CloudWatch (after 2-3 minutes)

1. Go to AWS Console → CloudWatch → Metrics
2. Navigate to: **Custom Namespaces** → **Harbor/Workers**
3. You should see metric: **QueueDepthPerWorker**
4. Click it to view the graph

You should see data points appearing every minute.

---

## Before You're Ready

**Important:** This metric publisher just publishes data. Auto-scaling is NOT enabled yet.

To enable auto-scaling, you need to add a **Target Tracking Policy** to your ASG.

---

## Adding Auto-Scaling Policy

Once you've verified the metric is working for a day or two, add the scaling policy:

### Option A: AWS Console

1. Go to EC2 → Auto Scaling Groups
2. Select your ASG (`harbor-workers-asg`)
3. Go to **Automatic scaling** tab
4. Click **Create dynamic scaling policy**
5. Select **Target tracking scaling**
6. Configure:
   - **Metric type**: Custom metric
   - **Namespace**: `Harbor/Workers`
   - **Metric name**: `QueueDepthPerWorker`
   - **Statistic**: Average
   - **Target value**: `60`
   - **Instances need**: `300` seconds warmup
   - **Scale-in**: Enable (be conservative)
7. Click **Create**

### Option B: AWS CLI

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name harbor-workers-asg \
  --policy-name queue-depth-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "CustomizedMetricSpecification": {
      "MetricName": "QueueDepthPerWorker",
      "Namespace": "Harbor/Workers",
      "Statistic": "Average",
      "Dimensions": [{
        "Name": "AutoScalingGroupName",
        "Value": "harbor-workers-asg"
      }]
    },
    "TargetValue": 60.0,
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }' \
  --region us-east-2
```

---

## Understanding the Target Value

**Target Value = 60** means:
- AWS tries to keep ~60 pending tasks per worker
- Each worker can handle 60 concurrent jobs (based on `--concurrency=60`)

**Examples:**

| Queue | Workers | Metric | Action |
|-------|---------|--------|--------|
| 300   | 5       | 60     | ✓ Perfect, no change |
| 600   | 5       | 120    | Scale UP: add 5 workers |
| 100   | 5       | 20     | Scale DOWN: remove 2-3 workers |
| 0     | 5       | 0      | Scale DOWN to min (2 workers) |

---

## Tuning the Target Value

After running for a while, you might want to adjust:

**If you want fewer workers (cheaper):**
- Increase target to 80-100
- Workers will handle more tasks each
- Slower response to spikes

**If you want faster response (expensive):**
- Decrease target to 40-50
- More workers, less load per worker
- Faster response to traffic

**Sweet spot for most:**
- Target: 60
- Matches your Celery concurrency
- Good balance of cost and responsiveness

---

## Monitoring Commands

```bash
# View metric publisher logs
tail -f /var/log/harbor-metric-publisher.log

# Check cron job is installed
crontab -l | grep harbor

# Test manually
/home/ubuntu/run_harbor_metric_publisher.sh

# Check Redis queue directly
redis-cli -h h-redis.yx44yl.ng.0001.use2.cache.amazonaws.com llen celery

# Check ASG status
aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names harbor-workers-asg \
  --region us-east-2 \
  --query 'AutoScalingGroups[0].[DesiredCapacity,MinSize,MaxSize]' \
  --output table
```

---

## Troubleshooting

### Metric not appearing in CloudWatch

**Check:** Script is running
```bash
tail /var/log/harbor-metric-publisher.log
```

If no output, check cron:
```bash
crontab -l
# Should show: * * * * * /home/ubuntu/run_harbor_metric_publisher.sh
```

**Check:** AWS credentials
```bash
aws sts get-caller-identity
# Should return your AWS account info
```

If not, the EC2 instance needs an IAM role with CloudWatch write permissions.

### Script failing with "ASG not found"

**Check:** ASG name is correct
```bash
cat /home/ubuntu/harbor-metric-publisher.env | grep ASG_NAME
```

Update if wrong:
```bash
nano /home/ubuntu/harbor-metric-publisher.env
# Change ASG_NAME=your-actual-asg-name
```

**Check:** ASG exists
```bash
aws autoscaling describe-auto-scaling-groups --region us-east-2
```

### Script failing with "Redis connection failed"

**Check:** Redis host is correct
```bash
cat /home/ubuntu/harbor-metric-publisher.env | grep REDIS_HOST
```

**Check:** Can reach Redis
```bash
redis-cli -h <REDIS_HOST> ping
# Should return: PONG
```

### Workers being killed mid-job

This means you need graceful shutdown. See: [SCALING_GUIDE.md](../SCALING_GUIDE.md) for lifecycle hook setup.

---

## IAM Permissions Required

The backend EC2 instance needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "autoscaling:DescribeAutoScalingGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Cost Impact

**Metric Publisher:**
- Runs every minute = 43,800 times/month
- CloudWatch custom metric: $0.30/metric/month
- **Cost: ~$0.30/month** (negligible)

**Auto-Scaling:**
- Scales workers based on demand
- Could save 50-70% on idle time costs
- Example: If you only need 10 workers during business hours instead of 24/7
  - Without scaling: 10 workers × 720 hours × $0.333/hr = $2,397/month
  - With scaling: 10 workers × 8 hours × 20 days + 2 workers × rest = ~$800/month
  - **Savings: ~$1,600/month**

---

## Next Steps

1. ✅ Run `setup_autoscaling_metric.sh`
2. ⏳ Wait 2-3 minutes
3. ✅ Check logs: `tail -f /var/log/harbor-metric-publisher.log`
4. ✅ Verify CloudWatch metric appears
5. ⏳ Watch for 24-48 hours to understand your traffic patterns
6. ✅ Add Target Tracking policy to ASG
7. ⏳ Monitor for a week, tune target value as needed
8. ✅ Add graceful shutdown (lifecycle hooks) if seeing killed jobs

---

## Support

- **Logs**: `/var/log/harbor-metric-publisher.log`
- **Config**: `/home/ubuntu/harbor-metric-publisher.env`
- **Script**: `/usr/local/bin/publish_harbor_metric.py`
- **Cron wrapper**: `/home/ubuntu/run_harbor_metric_publisher.sh`

For more details, see [SCALING_GUIDE.md](../SCALING_GUIDE.md)
