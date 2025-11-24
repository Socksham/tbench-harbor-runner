# Quick Start Guide: Distributed Worker Deployment

This is a condensed guide for deploying the distributed worker architecture. For full details, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Prerequisites

- 10× EC2 instances (t3.2xlarge) for workers
- 1× EC2/RDS for PostgreSQL
- 1× EC2/ElastiCache for Redis
- 1× EC2 for NFS storage (can reuse backend API server)
- Security groups configured (NFS: 2049, PostgreSQL: 5432, Redis: 6379)

## Deployment in 5 Steps

### Step 1: Set Up NFS Server (5 minutes)

On your storage server (Backend API or dedicated):

```bash
cd /path/to/tbench-harbor-runner/backend/deployment
sudo ./setup_nfs_server.sh
```

Note the server's IP address for next steps.

---

### Step 2: Deploy Backend API (10 minutes)

On Backend API server:

```bash
git clone https://github.com/Socksham/tbench-harbor-runner.git
cd tbench-harbor-runner/backend

# Install dependencies
sudo apt-get install -y python3 python3-pip
pip3 install -r requirements.txt

# Configure
nano .env
# Update: DATABASE_URL, REDIS_URL, JOBS_DIR=/shared/harbor-jobs/jobs

# Start API
./run.sh
```

---

### Step 3: Deploy Workers (10 minutes per worker)

**Automated deployment** - SSH into each worker and run:

```bash
# Download scripts
wget https://raw.githubusercontent.com/Socksham/tbench-harbor-runner/tree/scale/backend/deployment/setup_nfs_client.sh
wget https://raw.githubusercontent.com/Socksham/tbench-harbor-runner/tree/scale/backend/deployment/setup_worker.sh
wget https://raw.githubusercontent.com/Socksham/tbench-harbor-runner/tree/scale/backend/deployment/install_worker_service.sh
chmod +x *.sh

# Setup (replace IPs with your values)
sudo ./setup_nfs_client.sh <NFS_SERVER_IP>

./setup_worker.sh \
  <POSTGRES_IP> \
  <REDIS_IP> \
  <OPENROUTER_KEY> \
  60 \
  https://github.com/Socksham/tbench-harbor-runner.git

sudo ./install_worker_service.sh 60
sudo systemctl start harbor-worker
```

**Parallel deployment tip:** Use [tmux](https://github.com/tmux/tmux/wiki) or [Ansible](https://www.ansible.com/) to deploy all 10 workers simultaneously.

---

### Step 4: Verify Deployment (5 minutes)

On any worker:

```bash
# Run health check
cd ~/tbench-harbor-runner/backend/deployment
./health_check.sh

# Check worker status
sudo systemctl status harbor-worker

# View logs
sudo journalctl -u harbor-worker -f
```

On Backend API or any worker:

```bash
# List all workers
celery -A workers.harbor_worker inspect ping

# Should show 10 workers responding with "pong"
```

---

### Step 5: Test the System (10 minutes)

1. **Upload test task** via frontend
2. **Monitor worker logs** on any worker: `sudo journalctl -u harbor-worker -f`
3. **Check Redis queue**: `redis-cli -h <REDIS_IP> llen celery`
4. **Verify results** in database and `/shared/harbor-jobs/jobs/`

**Load test:**
- Upload 10 tasks → Should distribute across workers
- Upload 100 tasks → All workers should be active
- Upload 600 tasks → Full capacity test

---

## Architecture Diagram

```
Frontend (Next.js)
        ↓
Backend API (FastAPI)
        ↓
    Redis Queue
        ↓
┌───────┼───────┐
│       │       │
W1     W2  ... W10    (10 workers × 60 concurrency = 600 jobs)
│       │       │
└───────┼───────┘
        ↓
   NFS Storage
```

---

## Key Commands

### Worker Management

```bash
# Start worker
sudo systemctl start harbor-worker

# Stop worker
sudo systemctl stop harbor-worker

# Restart worker
sudo systemctl restart harbor-worker

# View logs
sudo journalctl -u harbor-worker -f

# Health check
~/tbench-harbor-runner/backend/deployment/health_check.sh
```

### Monitoring

```bash
# List active workers
celery -A workers.harbor_worker inspect ping

# View active tasks
celery -A workers.harbor_worker inspect active

# Check queue length
redis-cli -h <REDIS_IP> llen celery

# Worker stats
celery -A workers.harbor_worker inspect stats
```

---

## Troubleshooting

### Worker won't start

```bash
# Check logs
sudo journalctl -u harbor-worker -n 100 --no-pager

# Common fixes:
sudo mount -a  # Remount NFS
sudo systemctl restart docker  # Restart Docker
pip3 install -r requirements.txt  # Reinstall deps
```

### NFS issues

```bash
# Check mount
df -h | grep /shared/harbor-jobs

# Remount
sudo mount -a

# Test write access
touch /shared/harbor-jobs/.test && rm /shared/harbor-jobs/.test
```

### Tasks stuck in queue

```bash
# Check queue
redis-cli -h <REDIS_IP> llen celery

# Check workers are online
celery -A workers.harbor_worker inspect ping

# Restart all workers
# (Run on each worker)
sudo systemctl restart harbor-worker
```

---

## Scaling Operations

### Add more workers

1. Launch new EC2 instance
2. Run deployment scripts (same as Step 3)
3. Worker automatically joins pool

### Adjust concurrency

```bash
# Edit service file
sudo nano /etc/systemd/system/harbor-worker.service
# Change: --concurrency=60 to desired value

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart harbor-worker
```

---

## Cost Estimate

**AWS Resources (US East):**
- 10× t3.2xlarge workers @ $0.3328/hr = $3.33/hr
- 1× t3.medium backend @ $0.0416/hr = $0.04/hr
- 1× t3.small PostgreSQL @ $0.0208/hr = $0.02/hr
- 1× t3.small Redis @ $0.0208/hr = $0.02/hr
- NFS storage: ~$0.10/GB/month for 500GB = $50/month

**Total: ~$3.41/hr = ~$2,450/month** (24/7 operation)

**Cost optimization:**
- Use **Spot Instances** for workers (70% savings)
- Implement **auto-scaling** (scale down when idle)
- Use **Reserved Instances** for backend/DB (up to 60% savings)

---

## Support

- **Full deployment guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture details**: [SCALING_GUIDE.md](SCALING_GUIDE.md)
- **Health monitoring**: Run `./deployment/health_check.sh`
- **Worker service**: `systemctl status harbor-worker`

For issues, check logs first:
```bash
sudo journalctl -u harbor-worker -n 100 --no-pager
```

---

## Next Steps After Deployment

1. ✅ Set up monitoring (CloudWatch, Grafana)
2. ✅ Configure automated backups (PostgreSQL, NFS → S3)
3. ✅ Implement auto-scaling based on queue length
4. ✅ Set up alerting (worker down, high queue, errors)
5. ✅ Enable SSL/TLS for production
6. ✅ Implement log aggregation (CloudWatch Logs, ELK)
7. ✅ Configure rate limiting on API
8. ✅ Set up CI/CD for deployments

**You're now ready to handle 600 concurrent Harbor jobs!** 🚀
