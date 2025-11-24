# Creating AMI with Graceful Shutdown

## Current Status

Your test worker instance **i-0e2dc6f4968274349** now has:
- ✅ `harbor-termination-handler.service` running and enabled
- ✅ `harbor-worker.service` running with 60 worker processes
- ✅ Both services configured to auto-start on boot
- ✅ IMDSv2 authentication working
- ✅ Graceful shutdown with 40-minute timeout configured

## Create New AMI

### Step 1: Stop Services (Optional but Recommended)

SSH into the test worker and stop services before creating AMI:

```bash
ssh ubuntu@<test-worker-ip>
sudo systemctl stop harbor-worker.service
sudo systemctl stop harbor-termination-handler.service
```

This ensures clean state in the AMI.

### Step 2: Create AMI from Test Worker

```bash
# Create AMI from the test worker instance
aws ec2 create-image \
  --instance-id i-0e2dc6f4968274349 \
  --name "harbor-worker-with-graceful-shutdown-$(date +%Y%m%d-%H%M)" \
  --description "Harbor worker with graceful shutdown handler and 40-min timeout" \
  --region us-east-2 \
  --no-reboot
```

**Note**: Using `--no-reboot` means the instance stays running during AMI creation. If you want guaranteed consistency, remove this flag (instance will reboot).

### Step 3: Wait for AMI to be Available

```bash
# Get the AMI ID from previous command output, then:
aws ec2 describe-images \
  --image-ids ami-XXXXXXXXX \
  --region us-east-2 \
  --query 'Images[0].State' \
  --output text
```

Wait until it shows `available` (usually 5-10 minutes).

### Step 4: Update Launch Template

```bash
# Get current launch template details
aws ec2 describe-launch-template-versions \
  --launch-template-name harbor-worker-template \
  --region us-east-2 \
  --versions '$Latest'

# Create new version with new AMI
aws ec2 create-launch-template-version \
  --launch-template-name harbor-worker-template \
  --source-version '$Latest' \
  --launch-template-data '{"ImageId":"ami-XXXXXXXXX"}' \
  --region us-east-2

# Set the new version as default
aws ec2 modify-launch-template \
  --launch-template-name harbor-worker-template \
  --default-version '$Latest' \
  --region us-east-2
```

### Step 5: Test with Single Instance

Before updating the entire ASG, launch a single test instance:

```bash
# Launch test instance from new launch template
aws ec2 run-instances \
  --launch-template LaunchTemplateName=harbor-worker-template \
  --region us-east-2 \
  --count 1
```

SSH into it and verify:

```bash
# Check both services are running
systemctl status harbor-termination-handler.service
systemctl status harbor-worker.service

# Check logs
tail -f /var/log/harbor-termination-handler.log
tail -f /var/log/harbor-worker.log

# Verify Celery workers
ps aux | grep celery | grep -v grep | wc -l  # Should show ~61 processes
```

### Step 6: Update ASG to Use New AMI

Once verified, update the ASG:

```bash
# Option A: Update ASG to use latest launch template version
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name harbor-workers-asg \
  --launch-template LaunchTemplateName=harbor-worker-template,Version='$Latest' \
  --region us-east-2
```

**Important**: Existing instances will NOT automatically update. New instances launched by ASG will use the new AMI.

### Step 7: Refresh Instances (Optional)

If you want to replace all existing instances with new ones:

```bash
# Start instance refresh
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name harbor-workers-asg \
  --preferences MinHealthyPercentage=50,InstanceWarmup=300 \
  --region us-east-2
```

This will gradually replace old instances with new ones (50% at a time).

---

## What Happens with New Instances

When new instances launch from this AMI:

1. **On Boot**:
   - Both systemd services auto-start (we enabled them)
   - `harbor-termination-handler.service` starts polling for termination every 30 seconds
   - `harbor-worker.service` starts Celery with 60 workers

2. **During Normal Operation**:
   - Workers accept tasks from Redis queue
   - Termination handler quietly polls EC2 metadata (no log spam)

3. **During Scale-Down**:
   - ASG puts instance in `Terminating:Wait` state (lifecycle hook holds for 60 min)
   - Termination handler detects termination notice
   - Celery stops accepting new tasks
   - Waits up to 40 minutes for current jobs to finish
   - Signals AWS lifecycle action complete
   - Instance terminates

---

## Important Notes

### Path Configuration

The test worker uses: `/home/ubuntu/venv/bin/celery`

The `harbor-worker.service` file is configured with:
```ini
ExecStart=/home/ubuntu/venv/bin/celery -A workers.harbor_worker worker \
    --loglevel=info \
    --concurrency=60 \
    --max-tasks-per-child=50 \
    --hostname=worker-$(hostname)@%%h
```

Your existing ASG launch template user data:
```bash
#!/bin/bash
mount -a
timeout 60 bash -c 'until [ -d /shared/harbor-jobs/jobs ]; do sleep 2; done'
systemctl start harbor-worker
systemctl enable harbor-worker
echo "Harbor worker started at $(date)" >> /var/log/harbor-worker-startup.log
```

Since the launch template just runs `systemctl start harbor-worker`, it will use whatever service file is in the AMI.

### Environment Variables

Make sure your test worker's `.env` file has all necessary variables:
```bash
ssh ubuntu@<test-worker-ip>
cat /home/ubuntu/tbench-harbor-runner/backend/.env
```

These should include:
- `REDIS_URL`
- `DATABASE_URL`
- Any other config your Harbor workers need

---

## Troubleshooting New Instances

If new instances don't work:

### Check Service Status
```bash
systemctl status harbor-termination-handler.service
systemctl status harbor-worker.service
```

### Check Logs
```bash
tail -50 /var/log/harbor-termination-handler.log
tail -50 /var/log/harbor-worker.log
journalctl -u harbor-worker.service -n 50
```

### Check NFS Mount
```bash
df -h | grep shared
ls -la /shared/harbor-jobs/
```

### Check Celery Workers
```bash
ps aux | grep celery
```

### Common Issues

**Services not starting**: Check systemd service files exist
```bash
ls -la /etc/systemd/system/harbor-*
```

**Wrong Python path**: Check ExecStart in service file
```bash
cat /etc/systemd/system/harbor-worker.service | grep ExecStart
```

**Missing .env**: Check environment file exists
```bash
ls -la /home/ubuntu/tbench-harbor-runner/backend/.env
```

---

## Next Steps After AMI Creation

1. ✅ Create AMI from test worker
2. ✅ Update launch template with new AMI
3. ✅ Test single instance from new AMI
4. ✅ Update ASG to use new launch template
5. ⏭️ Add target tracking auto-scaling policy (see [AUTOSCALING_SETUP.md](AUTOSCALING_SETUP.md))
6. ⏭️ Monitor first scale-down event to verify graceful shutdown works

---

## Rollback Plan

If something goes wrong with the new AMI:

```bash
# Revert launch template to previous version
aws ec2 modify-launch-template \
  --launch-template-name harbor-worker-template \
  --default-version <previous-version-number> \
  --region us-east-2

# Update ASG
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name harbor-workers-asg \
  --launch-template LaunchTemplateName=harbor-worker-template,Version='<previous-version>' \
  --region us-east-2
```
