#!/bin/bash

# Terminal-Bench Harbor Runner - FastAPI Backend Startup Script

echo "Starting FastAPI backend..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration before running again."
    exit 1
fi

# Start FastAPI server
echo "Starting FastAPI server on http://localhost:8000"
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0

