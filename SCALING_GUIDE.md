# Scaling Guide: 600 Concurrent Jobs

## Current Problem

Your setup has:
- ✅ Separate EC2 instances for PostgreSQL, Redis, and Backend API
- ❌ **All Harbor jobs run on ONE machine** (`3.14.12.232`)

This creates a bottleneck. To run 600 jobs concurrently, you need **multiple worker machines**.

---

## Architecture: Distributed Worker Pool

```
┌─────────────────┐
│   Frontend      │
│   (Next.js)     │
└────────┬────────┘
         │
┌────────▼────────┐      ┌─────────────┐      ┌─────────────┐
│  Backend API    │─────▶│  Redis      │◀─────│ PostgreSQL  │
│   (FastAPI)     │      │  (Queue)    │      │ (Database)  │
│   EC2-1         │      │  EC2-2      │      │  EC2-3      │
└─────────────────┘      └──────┬──────┘      └─────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
         ┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
         │ Worker-1     │ │ Worker-2   │ │ Worker-N   │
         │ Celery+Harbor│ │ Celery+Harbor│ │ Celery+Harbor│
         │ + Docker     │ │ + Docker   │ │ + Docker   │
         │ EC2-4        │ │ EC2-5      │ │ EC2-N      │
         └──────────────┘ └────────────┘ └────────────┘
            (60 jobs)       (60 jobs)       (60 jobs)
```

---

## Solution 1: Local Execution on Multiple Workers (RECOMMENDED)

### How It Works:
- Each worker machine runs Celery worker + Harbor + Docker **locally**
- Celery distributes tasks across all workers via Redis
- Each worker handles 60 concurrent jobs (configurable)
- 10 workers × 60 jobs = **600 concurrent jobs**

### Setup Steps:

#### Step 1: Set Up Shared Storage (NFS)

Since workers need access to job files, set up NFS:

**On your storage server (can be Backend API server):**
```bash
# Install NFS server
sudo apt-get install nfs-kernel-server

# Create shared directory
sudo mkdir -p /shared/harbor-jobs
sudo chown nobody:nogroup /shared/harbor-jobs
sudo chmod 777 /shared/harbor-jobs

# Configure NFS exports
sudo nano /etc/exports
# Add this line:
# /shared/harbor-jobs *(rw,sync,no_subtree_check,no_root_squash)

# Apply changes
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

**On each worker machine:**
```bash
# Install NFS client
sudo apt-get install nfs-common

# Create mount point
sudo mkdir -p /shared/harbor-jobs

# Mount NFS share (replace NFS_SERVER_IP)
sudo mount NFS_SERVER_IP:/shared/harbor-jobs /shared/harbor-jobs

# Make it permanent
echo "NFS_SERVER_IP:/shared/harbor-jobs /shared/harbor-jobs nfs defaults 0 0" | sudo tee -a /etc/fstab
```

#### Step 2: Configure Backend to Use Shared Storage

Update your backend `.env`:
```bash
# On Backend API server
JOBS_DIR=/shared/harbor-jobs

# Disable remote execution (workers execute locally)
REMOTE_EXECUTION_ENABLED=false
REMOTE_HOST=
```

#### Step 3: Set Up Worker Machines

**Launch 10 EC2 instances** (e.g., t3.2xlarge or c5.4xlarge for 8-16 vCPUs each)

**On EACH worker machine, run:**

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip docker.io rsync nfs-common git

# 2. Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# 3. Install Harbor
pip install harbor-bench  # or pipx install harbor-bench

# 4. Clone your backend code
git clone <your-repo> /home/ubuntu/tbench-harbor-runner
cd /home/ubuntu/tbench-harbor-runner/backend

# 5. Install Python dependencies
pip install -r requirements.txt

# 6. Mount shared storage
sudo mkdir -p /shared/harbor-jobs
sudo mount NFS_SERVER_IP:/shared/harbor-jobs /shared/harbor-jobs

# 7. Create worker .env file
cat > .env << 'EOF'
# Database (point to your PostgreSQL EC2)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@POSTGRES_IP:5432/tbench

# Redis (point to your Redis EC2)
REDIS_URL=redis://REDIS_IP:6379/0

# OpenRouter
DEFAULT_OPENROUTER_KEY=your-key-here

# Local execution (each worker runs Harbor locally)
REMOTE_EXECUTION_ENABLED=false

# Shared storage (NFS mount)
JOBS_DIR=/shared/harbor-jobs
UPLOADS_DIR=/shared/harbor-jobs/uploads

# Harbor Settings
HARBOR_TIMEOUT_MULTIPLIER=1.0
MAX_CONCURRENT_RUNS_PER_WORKER=60  # Each worker handles 60 jobs

# Docker (local)
DOCKER_HOST=unix:///var/run/docker.sock
EOF

# 8. Start Celery worker
cd /home/ubuntu/tbench-harbor-runner/backend
nohup celery -A workers.harbor_worker worker \
  --loglevel=info \
  --concurrency=60 \
  --max-tasks-per-child=50 \
  > worker.log 2>&1 &
```

#### Step 4: Verify Setup

```bash
# Check Redis connection from worker
redis-cli -h REDIS_IP ping

# Check PostgreSQL connection from worker
psql -h POSTGRES_IP -U postgres -d tbench -c "SELECT 1;"

# Check NFS mount
ls /shared/harbor-jobs

# Monitor worker
tail -f worker.log
```

---

## Solution 2: Dynamic Worker Pool with Routing

If you want to keep remote execution but distribute across multiple machines:

### Implementation:

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create worker pool configuration system", "activeForm": "Creating worker pool configuration system", "status": "in_progress"}, {"content": "Modify harbor_service to support local execution on workers", "activeForm": "Modifying harbor_service to support local execution on workers", "status": "pending"}, {"content": "Create worker deployment script/documentation", "activeForm": "Creating worker deployment script/documentation", "status": "pending"}, {"content": "Update configuration to disable remote execution", "activeForm": "Updating configuration to disable remote execution", "status": "pending"}, {"content": "Create NFS/shared storage setup guide", "activeForm": "Creating NFS/shared storage setup guide", "status": "completed"}]