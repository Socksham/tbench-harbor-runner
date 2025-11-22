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

## Scaling

To scale to 600 concurrent runs:
- Run multiple Celery workers: `celery -A workers.harbor_worker worker --concurrency=10`
- Run 60 workers (10 concurrent each) = 600 concurrent tasks
- Use Redis Cluster for high availability
- Monitor with Flower: `celery -A workers.harbor_worker flower`

