#!/bin/bash

# Terminal-Bench Harbor Runner - Celery Worker Startup Script

set -e

# Configuration
CONCURRENCY="${1:-10}"  # Default to 10 if not specified
LOG_LEVEL="${2:-info}"  # Default to info

echo "============================================"
echo "Starting Harbor Celery Worker"
echo "============================================"
echo ""
echo "Configuration:"
echo "  Concurrency: $CONCURRENCY"
echo "  Log level: $LOG_LEVEL"
echo "  Hostname: $(hostname)"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found"
    echo ""
    if [ -f .env.worker.example ]; then
        echo "Worker template found. Creating .env from .env.worker.example..."
        cp .env.worker.example .env
        echo "Please edit .env with your configuration before running again."
    elif [ -f .env.example ]; then
        echo "Creating .env from .env.example..."
        cp .env.example .env
        echo "Please edit .env with your configuration before running again."
    else
        echo "No template found. Please create .env manually."
    fi
    exit 1
fi

# Verify required environment variables
echo "Verifying configuration..."
source .env

if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not set in .env"
    exit 1
fi

if [ -z "$REDIS_URL" ]; then
    echo "ERROR: REDIS_URL not set in .env"
    exit 1
fi

if [ -z "$JOBS_DIR" ]; then
    echo "ERROR: JOBS_DIR not set in .env"
    exit 1
fi

echo "✓ Database: ${DATABASE_URL%%@*}@..."
echo "✓ Redis: $REDIS_URL"
echo "✓ Jobs directory: $JOBS_DIR"
echo ""

# Check if jobs directory is accessible
if [ ! -d "$JOBS_DIR" ]; then
    echo "WARNING: Jobs directory does not exist: $JOBS_DIR"
    echo "If using NFS, make sure it's mounted!"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start Celery worker
echo "Starting Celery worker..."
echo "Command: celery -A workers.harbor_worker worker --loglevel=$LOG_LEVEL --concurrency=$CONCURRENCY"
echo ""

exec celery -A workers.harbor_worker worker \
    --loglevel=$LOG_LEVEL \
    --concurrency=$CONCURRENCY \
    --max-tasks-per-child=50 \
    --hostname="worker-$(hostname)@%h"

