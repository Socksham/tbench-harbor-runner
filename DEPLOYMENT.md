# Deployment Guide: Scaling to 600 Concurrent Jobs

This guide explains how to deploy the distributed worker architecture for running 600 concurrent Harbor tasks.

## Architecture Overview

```
┌──────────────┐
│   Frontend   │  (Next.js on Vercel/EC2)
│   Next.js    │
└──────┬───────┘
       │
┌──────▼───────┐      ┌─────────────┐      ┌─────────────┐
│ Backend API  │─────▶│   Redis     │      │ PostgreSQL  │
│   FastAPI    │      │   Queue     │      │  Database   │
│   EC2-API    │      │   EC2-Redis │      │  EC2-DB     │
└──────────────┘      └──────┬──────┘      └─────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼─────┐         ┌────▼────┐         ┌────▼────┐
    │Worker-1 │         │Worker-2 │   ...   │Worker-10│
    │Harbor   │         │Harbor   │         │Harbor   │
    │+Docker  │         │+Docker  │         │+Docker  │
    │EC2-W1   │         │EC2-W2   │         │EC2-W10  │
    └───┬─────┘         └────┬────┘         └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                      ┌──────▼──────┐
                      │ NFS Storage │
                      │/shared/jobs │
                      │ EC2-Storage │
                      └─────────────┘
```

**Scaling Calculation:**
- 10 worker EC2 instances
- Each worker: `--concurrency=60`
- Total: **10 × 60 = 600 concurrent Harbor jobs**

---

## Prerequisites

### AWS Resources Required

1. **VPC & Networking**
   - VPC with private subnet (recommended)
   - Security groups configured (see Security Group section below)

2. **EC2 Instances**
   - **Backend API**: 1× t3.medium (2 vCPU, 4GB RAM)
   - **PostgreSQL**: 1× t3.small (2 vCPU, 2GB RAM) or RDS instance
   - **Redis**: 1× t3.small (2 vCPU, 2GB RAM) or ElastiCache
   - **NFS Storage**: Can reuse Backend API or dedicated instance
   - **Workers**: 10× t3.2xlarge (8 vCPU, 32GB RAM each)

3. **Storage**
   - NFS server with sufficient disk space (500GB+ recommended)
   - Each Harbor job can generate 50-500MB of logs/results

### Security Group Configuration

#### Backend API Security Group
- Inbound: 8000 (from Frontend, Workers)
- Outbound: All

#### PostgreSQL Security Group
- Inbound: 5432 (from Backend API, Workers)
- Outbound: All

#### Redis Security Group
- Inbound: 6379 (from Backend API, Workers)
- Outbound: All

#### NFS Server Security Group
- Inbound: 2049 (from Workers)
- Outbound: All

#### Worker Security Group
- Outbound: All (needs internet for Docker images, LLM APIs)

---

## Deployment Steps

### Phase 1: Core Infrastructure Setup

#### 1.1 Set Up PostgreSQL

**Option A: EC2 with PostgreSQL**
```bash
# On PostgreSQL EC2
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# Configure PostgreSQL
sudo -u postgres psql
CREATE DATABASE tbench;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE tbench TO postgres;
\q

# Allow remote connections
sudo nano /etc/postgresql/*/main/postgresql.conf
# Set: listen_addresses = '*'

sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add: host all all 0.0.0.0/0 md5

sudo systemctl restart postgresql
```

**Option B: AWS RDS**
- Create PostgreSQL RDS instance
- Database name: `tbench`
- Note the connection endpoint

#### 1.2 Set Up Redis

**Option A: EC2 with Redis**
```bash
# On Redis EC2
sudo apt-get update
sudo apt-get install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: bind 0.0.0.0
# Set: protected-mode no

sudo systemctl restart redis-server
```

**Option B: AWS ElastiCache**
- Create Redis ElastiCache cluster
- Note the connection endpoint

#### 1.3 Set Up NFS Server

Run on the machine that will host shared storage (Backend API or dedicated storage server):

```bash
# Copy deployment scripts
cd /path/to/tbench-harbor-runner/backend/deployment

# Make scripts executable
chmod +x *.sh

# Run NFS server setup
sudo ./setup_nfs_server.sh

# Verify NFS is running
sudo systemctl status nfs-kernel-server
showmount -e localhost
```

**Note:** Edit the script to change the allowed subnet if needed (default: 10.0.0.0/16)

---

### Phase 2: Backend API Deployment

#### 2.1 Deploy Backend API

```bash
# On Backend API EC2
git clone https://github.com/YOUR_USERNAME/tbench-harbor-runner.git
cd tbench-harbor-runner/backend

# Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip postgresql-client redis-tools
pip3 install -r requirements.txt

# Configure environment
cp .env .env.backup  # Backup existing config
nano .env

# Update these values:
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@<POSTGRES_IP>:5432/tbench
# REDIS_URL=redis://<REDIS_IP>:6379/0
# JOBS_DIR=/shared/harbor-jobs/jobs
# UPLOADS_DIR=/shared/harbor-jobs/uploads
# DOCKER_HOST=  (leave empty)

# Run database migrations
python3 -c "from app.db.database import engine; from app.db.models import Base; import asyncio; asyncio.run(Base.metadata.create_all(bind=engine))"

# Start backend API
./run.sh
# Or use systemd service (create harbor-api.service)
```

#### 2.2 Deploy Frontend

```bash
# On Frontend server or Vercel
cd tbench-harbor-runner/frontend

# Update API URL
nano .env
# NEXT_PUBLIC_API_URL=http://<BACKEND_API_IP>:8000

# Install and build
npm install
npm run build
npm start
# Or deploy to Vercel
```

---

### Phase 3: Worker Deployment

#### 3.1 Launch Worker EC2 Instances

Launch 10 EC2 instances with:
- AMI: Ubuntu 22.04
- Instance type: t3.2xlarge (8 vCPU, 32GB RAM)
- Storage: 100GB SSD minimum
- Security group: Worker security group
- Key pair: Your SSH key

#### 3.2 Deploy Workers (Repeat for each instance)

**Automated Deployment (Recommended):**

```bash
# SSH into worker
ssh -i your-key.pem ubuntu@<WORKER_IP>

# Download deployment scripts
wget https://raw.githubusercontent.com/YOUR_USERNAME/tbench-harbor-runner/main/backend/deployment/setup_nfs_client.sh
wget https://raw.githubusercontent.com/YOUR_USERNAME/tbench-harbor-runner/main/backend/deployment/setup_worker.sh
wget https://raw.githubusercontent.com/YOUR_USERNAME/tbench-harbor-runner/main/backend/deployment/install_worker_service.sh
chmod +x *.sh

# 1. Set up NFS client
sudo ./setup_nfs_client.sh <NFS_SERVER_IP>

# 2. Deploy worker
./setup_worker.sh \
  <POSTGRES_IP> \
  <REDIS_IP> \
  <OPENROUTER_KEY> \
  60 \
  https://github.com/YOUR_USERNAME/tbench-harbor-runner.git

# 3. Install as systemd service
sudo ./install_worker_service.sh 60

# 4. Start service
sudo systemctl start harbor-worker
sudo systemctl status harbor-worker

# 5. Monitor logs
sudo journalctl -u harbor-worker -f
```

**Manual Deployment:**

See [SCALING_GUIDE.md](SCALING_GUIDE.md) for manual steps.

---

### Phase 4: Verification & Testing

#### 4.1 Verify Worker Connectivity

On each worker:

```bash
# Check NFS mount
df -h | grep /shared/harbor-jobs
ls -la /shared/harbor-jobs

# Check PostgreSQL connection
psql -h <POSTGRES_IP> -U postgres -d tbench -c "SELECT 1;"

# Check Redis connection
redis-cli -h <REDIS_IP> ping

# Check worker status
sudo systemctl status harbor-worker

# Check Celery logs
sudo journalctl -u harbor-worker -n 100
```

#### 4.2 Test Single Job

1. Upload a small test task via frontend
2. Monitor worker logs: `sudo journalctl -u harbor-worker -f`
3. Verify job completes successfully
4. Check results in database and NFS storage

#### 4.3 Load Testing

**Test 10 concurrent jobs:**
```bash
# Upload 10 tasks simultaneously via frontend
# Verify distribution across workers
```

**Test 100 concurrent jobs:**
```bash
# Upload 100 tasks
# Monitor Redis queue: redis-cli -h <REDIS_IP> llen celery
# Monitor worker CPU/memory on all instances
```

**Test 600 concurrent jobs:**
```bash
# Upload batch of tasks to reach 600 concurrent runs
# Monitor system health across all workers
# Verify no worker is overloaded
```

---

## Monitoring & Operations

### Worker Health Checks

Create a monitoring script on each worker:

```bash
cd ~/tbench-harbor-runner/backend/deployment
./health_check.sh
```

See [health_check.sh](backend/deployment/health_check.sh) for implementation.

### View Worker Status

**On Backend API or any worker:**
```bash
# List all Celery workers
celery -A workers.harbor_worker inspect active_queues

# Check active tasks
celery -A workers.harbor_worker inspect active

# Worker stats
celery -A workers.harbor_worker inspect stats
```

**Redis Queue Monitoring:**
```bash
# Connect to Redis
redis-cli -h <REDIS_IP>

# Check queue length
llen celery

# View tasks
lrange celery 0 10
```

### Log Locations

- **Backend API logs**: `./backend/` (console output)
- **Worker logs**: `sudo journalctl -u harbor-worker`
- **Harbor job logs**: `/shared/harbor-jobs/jobs/<job_id>/`
- **NFS logs**: `sudo journalctl -u nfs-kernel-server`

---

## Scaling Operations

### Add More Workers

To increase capacity beyond 600 jobs:

1. Launch new EC2 instance
2. Run worker deployment script
3. Workers automatically join the pool via Redis

**New capacity:** (N workers) × 60 = N × 60 concurrent jobs

### Remove Workers

To gracefully remove a worker:

```bash
# On the worker to remove
sudo systemctl stop harbor-worker

# Wait for current tasks to finish
celery -A workers.harbor_worker inspect active

# Once empty, decommission instance
```

### Adjust Worker Concurrency

To change concurrency on a worker:

```bash
# Edit systemd service
sudo nano /etc/systemd/system/harbor-worker.service
# Change --concurrency=60 to desired value

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart harbor-worker
```

---

## Troubleshooting

### Worker Won't Start

**Check logs:**
```bash
sudo journalctl -u harbor-worker -n 100 --no-pager
```

**Common issues:**
- NFS not mounted: `sudo mount -a`
- Redis unreachable: Check security group
- PostgreSQL connection failed: Verify credentials
- Python dependencies missing: `pip3 install -r requirements.txt`

### Tasks Stuck in Queue

**Diagnosis:**
```bash
# Check worker count
celery -A workers.harbor_worker inspect ping

# Check active tasks
celery -A workers.harbor_worker inspect active

# Check queue size
redis-cli -h <REDIS_IP> llen celery
```

**Solutions:**
- Restart workers: `sudo systemctl restart harbor-worker`
- Check worker logs for errors
- Verify workers can access NFS

### NFS Performance Issues

**Symptoms:**
- Slow file writes
- Harbor timeouts

**Solutions:**
- Use async NFS option: `async` instead of `sync` in exports
- Increase NFS server resources
- Use dedicated NFS instance with SSD storage
- Consider EFS instead of NFS on EC2

### High Memory Usage

**Monitor memory:**
```bash
# On worker
free -h
docker stats
```

**Solutions:**
- Reduce concurrency per worker
- Increase worker instance size
- Set memory limits in systemd service
- Ensure `--max-tasks-per-child=50` is set (prevents memory leaks)

---

## Cost Optimization

### Instance Sizing

**Recommended for production:**
- Workers: t3.2xlarge (8 vCPU, 32 GB) × 10 = ~$2.00/hour
- Backend: t3.medium = ~$0.04/hour
- PostgreSQL: t3.small = ~$0.02/hour
- Redis: t3.small = ~$0.02/hour

**Total:** ~$2.08/hour = ~$1,500/month (24/7)

**Cost reduction strategies:**
1. **Use Spot Instances for workers** (70% savings)
2. **Auto-scaling**: Scale workers up/down based on queue length
3. **Reserved Instances**: For Backend API, PostgreSQL, Redis
4. **S3 instead of NFS**: For completed job storage

### Auto-Scaling (Advanced)

Implement auto-scaling based on Redis queue length:

```python
# Monitor queue and scale workers
import boto3

redis_client = redis.Redis(host=REDIS_IP)
queue_length = redis_client.llen('celery')

if queue_length > 500:
    # Launch more workers
    ec2.run_instances(...)
elif queue_length < 100:
    # Terminate idle workers
    ...
```

---

## Security Considerations

1. **Network Security**
   - Use private subnets for workers
   - Restrict security groups to minimum required ports
   - Use VPN or bastion host for SSH access

2. **Data Security**
   - Encrypt NFS traffic (NFS over TLS)
   - Use encrypted EBS volumes
   - Rotate OpenRouter API keys regularly

3. **Access Control**
   - Use IAM roles for EC2 instances
   - Restrict S3/EFS access with IAM policies
   - Enable CloudTrail for audit logging

---

## Backup & Disaster Recovery

### Database Backups

**PostgreSQL:**
```bash
# Automated daily backups
pg_dump -h <POSTGRES_IP> -U postgres tbench > backup_$(date +%Y%m%d).sql

# Or use RDS automated backups
```

### Job Storage Backups

```bash
# Backup job files to S3
aws s3 sync /shared/harbor-jobs/ s3://your-backup-bucket/harbor-jobs/
```

### Recovery Procedures

1. **Worker failure**: Launch replacement, runs automatically via systemd
2. **NFS failure**: Restore from S3 backup, remount on workers
3. **Database failure**: Restore from RDS snapshot or pg_dump backup
4. **Redis failure**: Restart service, jobs will be re-queued

---

## Performance Tuning

### PostgreSQL Optimization

```sql
-- Increase connection pool
max_connections = 200

-- Tune for concurrent writes
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 16MB
```

### Redis Optimization

```conf
# Increase max memory
maxmemory 8gb
maxmemory-policy allkeys-lru

# Disable persistence for better performance (optional)
save ""
```

### NFS Optimization

```bash
# Use async for better performance
/shared/harbor-jobs *(rw,async,no_subtree_check,no_root_squash)

# Mount with performance options
mount -o rw,async,hard,intr <NFS_SERVER>:/shared/harbor-jobs /shared/harbor-jobs
```

---

## Next Steps

1. ✅ Deploy infrastructure (Phase 1-3)
2. ✅ Verify functionality (Phase 4)
3. 🔄 Monitor performance for 24 hours
4. 🔄 Tune configuration as needed
5. 🔄 Implement auto-scaling (optional)
6. 🔄 Set up automated backups
7. 🔄 Configure alerting (CloudWatch, PagerDuty)

---

## Support & Resources

- **SCALING_GUIDE.md**: Detailed architecture explanation
- **Backend deployment scripts**: `/backend/deployment/`
- **Health monitoring**: `/backend/deployment/health_check.sh`
- **Worker service**: `/backend/deployment/harbor-worker.service`

For issues or questions, refer to the project repository or contact the development team.
