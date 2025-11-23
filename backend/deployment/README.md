# Deployment Scripts

This directory contains all scripts needed to deploy the distributed worker architecture for scaling to 600 concurrent Harbor jobs.

## Scripts Overview

| Script | Purpose | Run On | Run As |
|--------|---------|--------|--------|
| `setup_nfs_server.sh` | Configure NFS server for shared storage | Storage server | root (sudo) |
| `setup_nfs_client.sh` | Mount NFS share on workers | Each worker | root (sudo) |
| `setup_worker.sh` | Complete worker deployment (automated) | Each worker | ubuntu |
| `harbor-worker.service` | Systemd service file template | Each worker | - |
| `install_worker_service.sh` | Install Harbor worker as systemd service | Each worker | root (sudo) |
| `health_check.sh` | Worker health and connectivity check | Each worker | ubuntu |

## Quick Deployment

### 1. NFS Server Setup

**On storage server (Backend API or dedicated):**

```bash
cd /path/to/tbench-harbor-runner/backend/deployment
sudo ./setup_nfs_server.sh
```

This will:
- Install NFS server
- Create `/shared/harbor-jobs` directory
- Configure NFS exports
- Start NFS service

**Note:** Edit the script to adjust the allowed subnet (default: 10.0.0.0/16)

---

### 2. Worker Deployment (Automated)

**On each worker EC2 instance:**

```bash
# Download deployment scripts
wget https://raw.githubusercontent.com/YOUR_USERNAME/tbench-harbor-runner/main/backend/deployment/setup_nfs_client.sh
wget https://raw.githubusercontent.com/YOUR_USERNAME/tbench-harbor-runner/main/backend/deployment/setup_worker.sh
wget https://raw.githubusercontent.com/YOUR_USERNAME/tbench-harbor-runner/main/backend/deployment/install_worker_service.sh
chmod +x *.sh

# 1. Mount NFS share
sudo ./setup_nfs_client.sh <NFS_SERVER_IP>

# 2. Deploy worker (all-in-one setup)
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
```

---

### 3. Health Check

**On any worker:**

```bash
cd ~/tbench-harbor-runner/backend/deployment
./health_check.sh
```

This checks:
- System resources (CPU, memory, disk)
- Docker service status
- Harbor worker service status
- Network connectivity (PostgreSQL, Redis)
- NFS mount and write access
- Celery worker status
- Active tasks and queue length

---

## Script Details

### setup_nfs_server.sh

**Purpose:** Configure NFS server for shared job storage

**What it does:**
1. Installs `nfs-kernel-server`
2. Creates `/shared/harbor-jobs` with proper permissions
3. Configures `/etc/exports` with NFS share settings
4. Starts and enables NFS server
5. Verifies configuration

**Configuration:**
- Shared directory: `/shared/harbor-jobs`
- Default subnet: `10.0.0.0/16` (edit in script)
- Permissions: `rw,sync,no_subtree_check,no_root_squash`

**Usage:**
```bash
sudo ./setup_nfs_server.sh
```

---

### setup_nfs_client.sh

**Purpose:** Mount NFS share on worker machines

**What it does:**
1. Installs `nfs-common` (NFS client)
2. Creates mount point `/shared/harbor-jobs`
3. Tests NFS connectivity
4. Mounts the NFS share
5. Adds to `/etc/fstab` for persistent mounting
6. Verifies write access

**Usage:**
```bash
sudo ./setup_nfs_client.sh <NFS_SERVER_IP>

# Example:
sudo ./setup_nfs_client.sh 10.0.1.100
```

**Troubleshooting:**
- **Connection failed:** Check security group allows port 2049
- **Write failed:** Check NFS export permissions (no_root_squash)
- **Mount failed:** Verify NFS server is running

---

### setup_worker.sh

**Purpose:** Complete worker deployment (all-in-one automation)

**What it does:**
1. Installs system dependencies (Python, Docker, Git, etc.)
2. Configures Docker and adds user to docker group
3. Installs Harbor CLI (`pip install harbor-bench`)
4. Clones repository
5. Installs Python dependencies
6. Creates `.env` configuration file
7. Verifies connections (PostgreSQL, Redis, NFS)
8. Provides next steps

**Usage:**
```bash
./setup_worker.sh <POSTGRES_IP> <REDIS_IP> [OPENROUTER_KEY] [CONCURRENCY] [REPO_URL]

# Example:
./setup_worker.sh 10.0.1.50 10.0.1.51 sk-or-v1-xxx 60 https://github.com/user/repo.git

# Minimal (uses defaults):
./setup_worker.sh 10.0.1.50 10.0.1.51
```

**Parameters:**
- `POSTGRES_IP`: PostgreSQL server IP (required)
- `REDIS_IP`: Redis server IP (required)
- `OPENROUTER_KEY`: API key (optional, can configure later)
- `CONCURRENCY`: Worker concurrency (default: 60)
- `REPO_URL`: Git repository (optional)

**Post-installation:**
- Repository installed at: `~/tbench-harbor-runner`
- Configuration file: `~/tbench-harbor-runner/backend/.env`
- Ready for systemd service installation

---

### install_worker_service.sh

**Purpose:** Install Harbor worker as systemd service for auto-start

**What it does:**
1. Verifies installation directory and `.env` exist
2. Copies `harbor-worker.service` to `/etc/systemd/system/`
3. Replaces placeholders (concurrency, username)
4. Reloads systemd daemon
5. Enables service (start on boot)
6. Optionally starts service immediately

**Usage:**
```bash
sudo ./install_worker_service.sh [CONCURRENCY] [USERNAME]

# Example:
sudo ./install_worker_service.sh 60 ubuntu

# With defaults:
sudo ./install_worker_service.sh
```

**Parameters:**
- `CONCURRENCY`: Celery concurrency (default: 60)
- `USERNAME`: System user (default: ubuntu)

**Service management:**
```bash
sudo systemctl start harbor-worker    # Start service
sudo systemctl stop harbor-worker     # Stop service
sudo systemctl restart harbor-worker  # Restart service
sudo systemctl status harbor-worker   # Check status
sudo journalctl -u harbor-worker -f   # View logs
```

---

### harbor-worker.service

**Purpose:** Systemd service template for Harbor worker

**Configuration:**
- User: ubuntu (configurable)
- Working directory: `/home/ubuntu/tbench-harbor-runner/backend`
- Command: `celery -A workers.harbor_worker worker --concurrency=60`
- Restart policy: Always restart on failure
- Timeout: 300 seconds for graceful shutdown
- Memory limit: 80% of system memory

**Manual installation:**
```bash
sudo cp harbor-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable harbor-worker
sudo systemctl start harbor-worker
```

---

### health_check.sh

**Purpose:** Comprehensive worker health and connectivity check

**What it checks:**
1. **System Resources**
   - CPU usage
   - Memory usage
   - Disk space

2. **Services**
   - Docker service status
   - Harbor worker service status
   - Process details (PID, CPU, memory)

3. **Network**
   - PostgreSQL connectivity
   - Redis connectivity
   - Redis queue length

4. **Storage**
   - NFS mount status
   - NFS available space
   - Write access test
   - Jobs directory accessibility

5. **Celery**
   - Worker process running
   - Active workers count
   - Active tasks count
   - Worker concurrency

6. **Logs**
   - Recent service logs (last 10 lines)

**Usage:**
```bash
./health_check.sh
```

**Exit codes:**
- `0`: Worker is healthy
- `1`: Worker has critical issues

**Example output:**
```
============================================
Harbor Worker Health Check
============================================
Hostname: worker-1
Date: 2025-11-23 10:30:00

============================================
1. System Resources
============================================
CPU Usage: 45.2%
✓ CPU usage normal
Memory: 12.5G / 31.2G (40.1%)
✓ Memory usage normal
Disk: 35% used, 50G available
✓ Disk space OK

[... more checks ...]

============================================
Summary
============================================
✓ Worker is healthy and ready
```

---

## Deployment Workflow

**Recommended deployment order:**

1. **Infrastructure Setup**
   ```bash
   # Launch EC2 instances
   # Configure security groups
   # Set up PostgreSQL and Redis
   ```

2. **NFS Server**
   ```bash
   # On storage server
   sudo ./setup_nfs_server.sh
   ```

3. **Backend API**
   ```bash
   # Deploy FastAPI backend
   # Update .env with NFS paths
   ```

4. **Workers (parallel)**
   ```bash
   # On each of 10 workers
   sudo ./setup_nfs_client.sh <NFS_IP>
   ./setup_worker.sh <PG_IP> <REDIS_IP> <KEY> 60
   sudo ./install_worker_service.sh 60
   ```

5. **Verification**
   ```bash
   # On each worker
   ./health_check.sh

   # On any machine with Celery
   celery -A workers.harbor_worker inspect ping
   ```

6. **Testing**
   ```bash
   # Upload test tasks
   # Monitor execution
   # Verify results
   ```

---

## Parallel Deployment

To deploy all 10 workers simultaneously, use one of these methods:

### Method 1: tmux

```bash
# Create tmux session with 10 panes
tmux new-session \; \
  split-window -v \; \
  split-window -v \; \
  # ... (create 10 panes)

# In each pane, SSH to a worker
ssh -i key.pem ubuntu@worker-N

# Run deployment commands synchronously across all panes
# Ctrl+B, :setw synchronize-panes on
```

### Method 2: Ansible

Create `deploy_workers.yml`:

```yaml
- hosts: workers
  become: yes
  vars:
    nfs_server_ip: 10.0.1.100
    postgres_ip: 10.0.1.50
    redis_ip: 10.0.1.51
    openrouter_key: "{{ lookup('env', 'OPENROUTER_KEY') }}"
  tasks:
    - name: Download deployment scripts
      get_url:
        url: "{{ item }}"
        dest: /home/ubuntu/{{ item | basename }}
        mode: '0755'
      loop:
        - https://raw.githubusercontent.com/.../setup_nfs_client.sh
        - https://raw.githubusercontent.com/.../setup_worker.sh
        - https://raw.githubusercontent.com/.../install_worker_service.sh

    - name: Setup NFS client
      command: /home/ubuntu/setup_nfs_client.sh {{ nfs_server_ip }}

    - name: Deploy worker
      become: no
      command: >
        /home/ubuntu/setup_worker.sh
        {{ postgres_ip }}
        {{ redis_ip }}
        {{ openrouter_key }}
        60

    - name: Install systemd service
      command: /home/ubuntu/install_worker_service.sh 60
```

Run: `ansible-playbook -i inventory.ini deploy_workers.yml`

### Method 3: AWS Systems Manager

Use SSM Run Command to execute scripts on all workers simultaneously.

---

## Environment Variables

All scripts respect these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SHARED_DIR` | NFS mount point | `/shared/harbor-jobs` |
| `INSTALL_DIR` | Worker installation directory | `$HOME/tbench-harbor-runner` |
| `CONCURRENCY` | Celery worker concurrency | `60` |
| `USERNAME` | System user | `ubuntu` |

---

## Troubleshooting

### NFS Issues

**Problem:** NFS won't mount

**Solutions:**
```bash
# Check NFS server is exporting
showmount -e <NFS_SERVER_IP>

# Check security group allows port 2049
nc -zv <NFS_SERVER_IP> 2049

# Try manual mount
sudo mount -t nfs <NFS_SERVER_IP>:/shared/harbor-jobs /shared/harbor-jobs

# Check NFS server logs
sudo journalctl -u nfs-kernel-server
```

---

### Worker Won't Start

**Problem:** Harbor worker service fails to start

**Solutions:**
```bash
# Check logs
sudo journalctl -u harbor-worker -n 50 --no-pager

# Common issues:
# 1. Missing dependencies
pip3 install -r requirements.txt

# 2. Docker not accessible
sudo usermod -aG docker ubuntu
newgrp docker

# 3. NFS not mounted
sudo mount -a

# 4. Database connection failed
psql -h <POSTGRES_IP> -U postgres -d tbench -c "SELECT 1;"

# 5. Redis connection failed
redis-cli -h <REDIS_IP> ping
```

---

### Health Check Failures

**Problem:** `health_check.sh` reports issues

**Solutions:**

```bash
# Run health check with verbose output
./health_check.sh

# Fix specific issues based on output:

# CPU/Memory high:
# - Reduce concurrency
# - Upgrade instance type
# - Kill runaway processes

# Disk space low:
# - Clean old job files
# - Increase EBS volume size
# - Add log rotation

# Service not running:
sudo systemctl start harbor-worker
sudo systemctl start docker

# Network issues:
# - Check security groups
# - Verify IP addresses in .env
# - Test with nc/telnet

# NFS issues:
sudo mount -a
sudo systemctl restart nfs-kernel-server
```

---

## Best Practices

1. **Security**
   - Use private subnets for workers
   - Restrict security groups to minimum required
   - Rotate API keys regularly
   - Use IAM roles instead of hardcoded credentials

2. **Monitoring**
   - Run `health_check.sh` periodically (cron job)
   - Set up CloudWatch metrics
   - Configure alerting for worker failures
   - Monitor NFS I/O and latency

3. **Backups**
   - Backup NFS to S3 daily
   - Automate PostgreSQL backups
   - Keep deployment scripts in version control

4. **Performance**
   - Tune PostgreSQL connection pool
   - Use async NFS options for better performance
   - Monitor and optimize Celery task times
   - Scale workers based on queue length

5. **Cost Optimization**
   - Use Spot Instances for workers (70% savings)
   - Implement auto-scaling
   - Use Reserved Instances for backend
   - Clean up old job files regularly

---

## Support

For more information:
- **Full deployment guide**: [/DEPLOYMENT.md](/DEPLOYMENT.md)
- **Quick start**: [/QUICK_START.md](/QUICK_START.md)
- **Scaling architecture**: [/SCALING_GUIDE.md](/SCALING_GUIDE.md)

For issues, check logs first:
```bash
sudo journalctl -u harbor-worker -n 100 --no-pager
```
