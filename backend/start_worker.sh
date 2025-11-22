#!/bin/bash

# Terminal-Bench Harbor Runner - Celery Worker Startup Script

echo "Starting Celery worker..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration before running again."
    exit 1
fi

# Start Celery worker
echo "Starting Celery worker with concurrency=10"
celery -A workers.harbor_worker worker --loglevel=info --concurrency=10

