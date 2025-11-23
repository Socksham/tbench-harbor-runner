# Terminal-Bench Harbor Runner - FastAPI Backend

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Harbor:
```bash
pip install harbor
# OR
uv tool install harbor
```

3. Set up PostgreSQL and Redis:
```bash
# Using Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres
docker run -d -p 6379:6379 redis

# Create the database (replace CONTAINER_ID with your PostgreSQL container ID)
docker exec CONTAINER_ID psql -U postgres -c "CREATE DATABASE tbench;"
# Or find container ID first:
docker ps --filter "ancestor=postgres" --format "{{.ID}}"
```

4. Create `.env` file from `.env.example`:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run database migrations (creates tables):
```bash
python -m app.main
```

6. Start FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

7. Start Celery worker (in separate terminal):
```bash
celery -A workers.harbor_worker worker --loglevel=info --concurrency=10
```

## API Endpoints

- `POST /api/upload` - Upload a zipped task
  - Form data:
    - `file`: zip file
    - `harness`: "harbor" or "terminus"
    - `model`: model identifier (e.g., "openai/gpt-4o")
    - `openrouter_key`: OpenRouter API key
    - `n_runs`: number of runs (default: 10)

- `GET /api/jobs/{job_id}` - Get job status and runs

- `GET /api/jobs/{job_id}/runs/{run_number}/logs/stream` - Stream logs (SSE)

## Testing

Test the upload endpoint:
```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@task.zip" \
  -F "harness=harbor" \
  -F "model=openai/gpt-4o" \
  -F "openrouter_key=your_key" \
  -F "n_runs=10"
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── api/                 # API routes
│   │   ├── upload.py        # Upload endpoint
│   │   ├── jobs.py          # Job management
│   │   └── logs.py           # Log streaming
│   ├── services/            # Business logic
│   │   ├── harbor_service.py
│   │   ├── task_extractor.py
│   │   ├── result_parser.py
│   │   └── job_manager.py
│   ├── models/              # Pydantic schemas
│   │   └── schemas.py
│   └── db/                  # Database
│       ├── database.py
│       └── models.py
└── workers/                 # Celery workers
    └── harbor_worker.py
```

## Remote Docker Configuration

For cloud deployments where Docker-in-Docker isn't supported, you can configure Harbor to use a remote Docker daemon.

1. **Set environment variables in `.env`:**
```bash
DOCKER_HOST=tcp://your-remote-docker-host:2376
DOCKER_TLS_VERIFY=0  # Set to "1" for TLS
# DOCKER_CERT_PATH=/path/to/certs  # Required if using TLS
```

2. **Test your configuration:**
```bash
python test_docker_host.py
```

3. **See detailed setup guide:**
```bash
cat DOCKER_REMOTE_SETUP.md
```

## Remote Execution (Recommended for Cloud)

For better reliability and to avoid volume mount issues, you can run Harbor directly on a remote host (e.g., EC2) where Docker is also running. This ensures Harbor and Docker are on the same machine, so volume mounts work correctly.

### Setup

1. **Install Harbor on remote host:**
```bash
ssh ubuntu@your-ec2-ip

# Option 1: Using pipx (recommended for Ubuntu 24.04+)
sudo apt update
sudo apt install -y pipx
pipx ensurepath
pipx install harbor

# Option 2: Using uv (if you have uv installed)
uv tool install harbor

# Option 3: Using virtual environment
python3 -m venv ~/harbor-venv
source ~/harbor-venv/bin/activate
pip install harbor

# Verify installation
harbor --version

# Create work directory
mkdir -p /home/ubuntu/harbor-jobs
```

2. **Configure environment variables in `.env`:**
```bash
# Enable remote execution
REMOTE_EXECUTION_ENABLED=true
REMOTE_HOST=ubuntu@your-ec2-ip-address
REMOTE_SSH_KEY_PATH=/path/to/your/ec2-key.pem
REMOTE_WORK_DIR=/home/ubuntu/harbor-jobs
REMOTE_SSH_PORT=22  # Default SSH port

# Don't set DOCKER_HOST when using remote execution
# Harbor will use local Docker on the remote host
```

3. **Ensure SSH access works:**
```bash
ssh -i /path/to/your/ec2-key.pem ubuntu@your-ec2-ip
```

4. **Restart Celery worker** to pick up new configuration

### How It Works

1. **File Transfer**: Task files are copied to the remote host using `rsync`
2. **Harbor Execution**: Harbor runs on the remote host using local Docker
3. **Result Retrieval**: Results are copied back using `rsync`
4. **Result Parsing**: Results are parsed the same way as local execution

### Benefits

- ✅ Volume mounts work correctly (Harbor and Docker on same host)
- ✅ No path issues (all paths are local to remote host)
- ✅ Better performance (no network latency for Docker operations)
- ✅ Isolation (Harbor execution isolated on remote host)

### Requirements

- SSH access to remote host
- Harbor installed on remote host
- Docker installed and running on remote host
- `rsync` available on both local and remote hosts

## Scaling

To scale to 600 concurrent runs:
- Run multiple Celery workers: `celery -A workers.harbor_worker worker --concurrency=10`
- Run 60 workers (10 concurrent each) = 600 concurrent tasks
- Use Redis Cluster for high availability
- Monitor with Flower: `celery -A workers.harbor_worker flower`
- For cloud deployments, use remote Docker daemon (see Remote Docker Configuration above)

