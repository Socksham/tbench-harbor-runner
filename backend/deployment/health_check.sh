#!/bin/bash

#############################################
# Harbor Worker Health Check Script
# Run this to verify worker health and connectivity
#############################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SHARED_DIR="/shared/harbor-jobs"
BACKEND_DIR="$HOME/tbench-harbor-runner/backend"

echo "============================================"
echo "Harbor Worker Health Check"
echo "============================================"
echo "Hostname: $(hostname)"
echo "Date: $(date)"
echo ""

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Load environment
if [ -f "$BACKEND_DIR/.env" ]; then
    source "$BACKEND_DIR/.env"
else
    check_fail ".env file not found at $BACKEND_DIR/.env"
    exit 1
fi

echo "============================================"
echo "1. System Resources"
echo "============================================"

# CPU
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
echo "CPU Usage: ${CPU_USAGE}%"
if (( $(echo "$CPU_USAGE > 90" | bc -l) )); then
    check_warn "High CPU usage"
else
    check_pass "CPU usage normal"
fi

# Memory
MEM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')
MEM_USED=$(free -h | awk '/^Mem:/ {print $3}')
MEM_PERCENT=$(free | awk '/^Mem:/ {printf("%.1f"), $3/$2 * 100}')
echo "Memory: $MEM_USED / $MEM_TOTAL (${MEM_PERCENT}%)"
if (( $(echo "$MEM_PERCENT > 90" | bc -l) )); then
    check_warn "High memory usage"
else
    check_pass "Memory usage normal"
fi

# Disk
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
echo "Disk: ${DISK_USAGE}% used, $DISK_AVAIL available"
if [ "$DISK_USAGE" -gt 90 ]; then
    check_warn "Low disk space"
else
    check_pass "Disk space OK"
fi

echo ""
echo "============================================"
echo "2. Service Status"
echo "============================================"

# Docker
if systemctl is-active --quiet docker; then
    check_pass "Docker service running"
    DOCKER_CONTAINERS=$(docker ps -q | wc -l)
    echo "  Active containers: $DOCKER_CONTAINERS"
else
    check_fail "Docker service not running"
fi

# Harbor Worker
if systemctl is-active --quiet harbor-worker 2>/dev/null; then
    check_pass "Harbor worker service running"

    # Get process details
    WORKER_PID=$(systemctl show harbor-worker -p MainPID | cut -d= -f2)
    if [ "$WORKER_PID" != "0" ]; then
        WORKER_CPU=$(ps -p $WORKER_PID -o %cpu= 2>/dev/null || echo "N/A")
        WORKER_MEM=$(ps -p $WORKER_PID -o %mem= 2>/dev/null || echo "N/A")
        echo "  Worker PID: $WORKER_PID (CPU: ${WORKER_CPU}%, MEM: ${WORKER_MEM}%)"
    fi
else
    check_warn "Harbor worker service not running (may be manual mode)"
fi

echo ""
echo "============================================"
echo "3. Network Connectivity"
echo "============================================"

# PostgreSQL
if [ -n "$DATABASE_URL" ]; then
    POSTGRES_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    POSTGRES_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    if nc -z -w5 $POSTGRES_HOST $POSTGRES_PORT 2>/dev/null; then
        check_pass "PostgreSQL reachable ($POSTGRES_HOST:$POSTGRES_PORT)"
    else
        check_fail "PostgreSQL unreachable ($POSTGRES_HOST:$POSTGRES_PORT)"
    fi
else
    check_warn "DATABASE_URL not set"
fi

# Redis
if [ -n "$REDIS_URL" ]; then
    REDIS_HOST=$(echo $REDIS_URL | sed -n 's|.*://\([^:]*\):.*|\1|p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')

    if nc -z -w5 $REDIS_HOST $REDIS_PORT 2>/dev/null; then
        check_pass "Redis reachable ($REDIS_HOST:$REDIS_PORT)"

        # Check queue length
        if command -v redis-cli &> /dev/null; then
            QUEUE_LENGTH=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT llen celery 2>/dev/null || echo "N/A")
            echo "  Queue length: $QUEUE_LENGTH tasks"
        fi
    else
        check_fail "Redis unreachable ($REDIS_HOST:$REDIS_PORT)"
    fi
else
    check_warn "REDIS_URL not set"
fi

echo ""
echo "============================================"
echo "4. Storage"
echo "============================================"

# NFS Mount
if [ -d "$SHARED_DIR" ]; then
    if mountpoint -q "$SHARED_DIR" 2>/dev/null; then
        check_pass "NFS mounted at $SHARED_DIR"

        # Check available space
        NFS_AVAIL=$(df -h $SHARED_DIR | awk 'NR==2 {print $4}')
        NFS_USED=$(df -h $SHARED_DIR | awk 'NR==2 {print $5}')
        echo "  Available: $NFS_AVAIL (Used: $NFS_USED)"

        # Test write access
        TEST_FILE="$SHARED_DIR/.health_check_$(hostname)_$(date +%s)"
        if touch "$TEST_FILE" 2>/dev/null; then
            check_pass "NFS write access OK"
            rm -f "$TEST_FILE"
        else
            check_fail "NFS write access failed"
        fi
    else
        check_fail "NFS not mounted at $SHARED_DIR"
    fi
else
    check_warn "Shared directory does not exist: $SHARED_DIR"
fi

# Jobs directory
if [ -n "$JOBS_DIR" ] && [ -d "$JOBS_DIR" ]; then
    JOB_COUNT=$(find "$JOBS_DIR" -maxdepth 1 -type d 2>/dev/null | wc -l)
    check_pass "Jobs directory accessible ($JOB_COUNT job directories)"
else
    check_warn "Jobs directory not accessible: $JOBS_DIR"
fi

echo ""
echo "============================================"
echo "5. Celery Worker Status"
echo "============================================"

cd "$BACKEND_DIR"

# Check if Celery is running
if pgrep -f "celery.*harbor_worker" > /dev/null; then
    check_pass "Celery worker process running"

    # Get worker info
    CELERY_WORKERS=$(celery -A workers.harbor_worker inspect ping 2>/dev/null | grep -c "pong" || echo "0")
    echo "  Active workers: $CELERY_WORKERS"

    # Get active tasks
    ACTIVE_TASKS=$(celery -A workers.harbor_worker inspect active 2>/dev/null | grep -c "id" || echo "0")
    echo "  Active tasks: $ACTIVE_TASKS"

    # Get concurrency
    CONCURRENCY=$(celery -A workers.harbor_worker inspect stats 2>/dev/null | grep -o '"pool": {"max-concurrency": [0-9]*' | grep -o '[0-9]*$' | head -1 || echo "N/A")
    echo "  Concurrency: $CONCURRENCY"
else
    check_warn "Celery worker process not found"
fi

echo ""
echo "============================================"
echo "6. Recent Logs (last 10 lines)"
echo "============================================"

if systemctl is-active --quiet harbor-worker 2>/dev/null; then
    sudo journalctl -u harbor-worker -n 10 --no-pager 2>/dev/null || echo "Cannot read logs (need sudo)"
else
    echo "No systemd service logs (worker may be running manually)"
fi

echo ""
echo "============================================"
echo "Summary"
echo "============================================"

# Overall health check
HEALTH_OK=true

# Critical checks
if ! systemctl is-active --quiet docker; then
    HEALTH_OK=false
fi

if [ -n "$REDIS_URL" ]; then
    REDIS_HOST=$(echo $REDIS_URL | sed -n 's|.*://\([^:]*\):.*|\1|p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
    if ! nc -z -w5 $REDIS_HOST $REDIS_PORT 2>/dev/null; then
        HEALTH_OK=false
    fi
fi

if [ -d "$SHARED_DIR" ] && ! mountpoint -q "$SHARED_DIR" 2>/dev/null; then
    HEALTH_OK=false
fi

if $HEALTH_OK; then
    echo -e "${GREEN}✓ Worker is healthy and ready${NC}"
    exit 0
else
    echo -e "${RED}✗ Worker has issues that need attention${NC}"
    exit 1
fi
