#!/bin/bash

#############################################
# Worker Deployment Script
# Run this on each EC2 worker instance to set up Harbor worker
#############################################

set -e  # Exit on any error

echo "============================================"
echo "Harbor Worker Deployment"
echo "============================================"
echo ""

# Check if running as regular user (not root)
if [[ $EUID -eq 0 ]]; then
   echo "WARNING: Do not run this script as root. Run as regular user (ubuntu)."
   echo "The script will use sudo when needed."
   exit 1
fi

# Get configuration from arguments or prompt
POSTGRES_IP="${1:-}"
REDIS_IP="${2:-}"
OPENROUTER_KEY="${3:-}"
CONCURRENCY="${4:-60}"
REPO_URL="${5:-https://github.com/YOUR_USERNAME/tbench-harbor-runner.git}"

if [ -z "$POSTGRES_IP" ] || [ -z "$REDIS_IP" ]; then
    echo "ERROR: Missing required arguments"
    echo ""
    echo "Usage: ./setup_worker.sh <POSTGRES_IP> <REDIS_IP> [OPENROUTER_KEY] [CONCURRENCY] [REPO_URL]"
    echo ""
    echo "Arguments:"
    echo "  POSTGRES_IP    - PostgreSQL server IP address"
    echo "  REDIS_IP       - Redis server IP address"
    echo "  OPENROUTER_KEY - OpenRouter API key (optional, can configure later)"
    echo "  CONCURRENCY    - Celery worker concurrency (default: 60)"
    echo "  REPO_URL       - Git repository URL (optional)"
    echo ""
    echo "Example:"
    echo "  ./setup_worker.sh 10.0.1.50 10.0.1.51 sk-or-v1-xxx 60"
    exit 1
fi

echo "Configuration:"
echo "  - PostgreSQL: $POSTGRES_IP"
echo "  - Redis: $REDIS_IP"
echo "  - Concurrency: $CONCURRENCY"
echo "  - OpenRouter Key: ${OPENROUTER_KEY:0:20}..."
echo ""
read -p "Continue with installation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

INSTALL_DIR="$HOME/tbench-harbor-runner"
SHARED_DIR="/shared/harbor-jobs"

echo ""
echo "============================================"
echo "Step 1: System Dependencies"
echo "============================================"
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    git \
    curl \
    postgresql-client \
    redis-tools

echo ""
echo "============================================"
echo "Step 2: Docker Configuration"
echo "============================================"
# Add user to docker group
sudo usermod -aG docker $USER

# Enable Docker service
sudo systemctl enable docker
sudo systemctl start docker

echo "Testing Docker access..."
# Use sg to test docker in same session
sg docker -c "docker ps" || echo "Note: You may need to log out and back in for docker group to take effect"

echo ""
echo "============================================"
echo "Step 3: Install Harbor"
echo "============================================"
# Install Harbor via pip
pip3 install --user harbor-bench

# Add to PATH if not already there
if ! grep -q '.local/bin' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
export PATH="$HOME/.local/bin:$PATH"

# Verify Harbor installation
harbor --version || echo "Harbor installation verification - may need to reload shell"

echo ""
echo "============================================"
echo "Step 4: Clone Repository"
echo "============================================"
if [ -d "$INSTALL_DIR" ]; then
    echo "Repository already exists at $INSTALL_DIR"
    read -p "Delete and re-clone? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf $INSTALL_DIR
        git clone $REPO_URL $INSTALL_DIR
    else
        echo "Keeping existing repository, pulling latest changes..."
        cd $INSTALL_DIR
        git pull
    fi
else
    git clone $REPO_URL $INSTALL_DIR
fi

cd $INSTALL_DIR/backend

echo ""
echo "============================================"
echo "Step 5: Python Dependencies"
echo "============================================"
pip3 install --user -r requirements.txt

echo ""
echo "============================================"
echo "Step 6: Configure Worker Environment"
echo "============================================"

# Create .env file for worker
cat > .env << EOF
# ============================================
# HARBOR WORKER CONFIGURATION
# ============================================
# This worker is part of a distributed pool.

# Database (shared PostgreSQL instance)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@$POSTGRES_IP:5432/tbench

# Redis (shared task queue)
REDIS_URL=redis://$REDIS_IP:6379/0

# OpenRouter API Key
DEFAULT_OPENROUTER_KEY=$OPENROUTER_KEY

# Shared Storage (NFS mount)
# Make sure NFS is mounted at this location!
JOBS_DIR=$SHARED_DIR/jobs
UPLOADS_DIR=$SHARED_DIR/uploads

# Harbor Settings
HARBOR_TIMEOUT_MULTIPLIER=1.0

# Docker (local socket - worker runs Docker locally)
DOCKER_HOST=
DOCKER_TLS_VERIFY=0

# CORS (not used by workers, but required by config)
CORS_ORIGINS=["http://localhost:3000"]
EOF

echo "✅ Worker .env created"

echo ""
echo "============================================"
echo "Step 7: Verify Connections"
echo "============================================"

echo "Testing PostgreSQL connection..."
if PGPASSWORD=postgres psql -h $POSTGRES_IP -U postgres -d tbench -c "SELECT 1;" &> /dev/null; then
    echo "  ✅ PostgreSQL connection successful"
else
    echo "  ❌ PostgreSQL connection failed"
    echo "  Please check:"
    echo "    - PostgreSQL server is running"
    echo "    - Security group allows port 5432"
    echo "    - Password is correct (default: postgres)"
fi

echo ""
echo "Testing Redis connection..."
if redis-cli -h $REDIS_IP ping &> /dev/null; then
    echo "  ✅ Redis connection successful"
else
    echo "  ❌ Redis connection failed"
    echo "  Please check:"
    echo "    - Redis server is running"
    echo "    - Security group allows port 6379"
fi

echo ""
echo "Testing NFS mount..."
if [ -d "$SHARED_DIR" ] && mountpoint -q "$SHARED_DIR"; then
    echo "  ✅ NFS mounted at $SHARED_DIR"
    # Test write access
    TEST_FILE="$SHARED_DIR/.worker_test_$(hostname)_$(date +%s)"
    if touch $TEST_FILE 2>/dev/null; then
        echo "  ✅ NFS write access confirmed"
        rm -f $TEST_FILE
    else
        echo "  ❌ NFS write access failed"
    fi
else
    echo "  ❌ NFS not mounted at $SHARED_DIR"
    echo "  Run setup_nfs_client.sh first!"
fi

echo ""
echo "============================================"
echo "Installation Summary"
echo "============================================"
echo "✅ System dependencies installed"
echo "✅ Docker configured"
echo "✅ Harbor installed"
echo "✅ Repository cloned to: $INSTALL_DIR"
echo "✅ Python dependencies installed"
echo "✅ Worker configuration created"
echo ""
echo "Worker Details:"
echo "  - Hostname: $(hostname)"
echo "  - Working directory: $INSTALL_DIR/backend"
echo "  - Concurrency: $CONCURRENCY"
echo "  - NFS mount: $SHARED_DIR"
echo ""
echo "Next steps:"
echo "  1. Set up systemd service (see harbor-worker.service)"
echo "  2. Or start manually:"
echo "     cd $INSTALL_DIR/backend"
echo "     celery -A workers.harbor_worker worker --loglevel=info --concurrency=$CONCURRENCY"
echo ""
echo "To set up as systemd service, run:"
echo "  sudo ./deployment/install_worker_service.sh $CONCURRENCY"
echo ""
