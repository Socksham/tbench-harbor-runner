# Terminal-Bench Harbor Runner

A scalable web platform for running Terminal-Bench tasks using the Harbor harness (Terminal-Bench 2). Upload tasks, run AI agents through them multiple times, and view detailed results and logs.

## Features

- ✅ **Batch Upload:** Upload multiple Terminal-Bench tasks simultaneously
- ✅ **Multiple Runs:** Run each task 1-100 times for statistical analysis
- ✅ **Real-time Monitoring:** Live log streaming and status updates
- ✅ **Harbor Integration:** Full Terminal-Bench 2 support with Docker
- ✅ **Multi-Model Support:** Any OpenRouter model (GPT-4, Claude, etc.)
- ✅ **Distributed Architecture:** Scale to 600+ concurrent jobs
- ✅ **Result Tracking:** Detailed test results and pass/fail rates

## Architecture

```
┌──────────────┐
│   Frontend   │  Next.js + TypeScript + Tailwind
│   (Next.js)  │
└──────┬───────┘
       │
┌──────▼───────┐      ┌─────────────┐      ┌─────────────┐
│ Backend API  │─────▶│   Redis     │      │ PostgreSQL  │
│  (FastAPI)   │      │   Queue     │      │  Database   │
└──────────────┘      └──────┬──────┘      └─────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼─────┐         ┌────▼────┐         ┌────▼────┐
    │Worker-1 │         │Worker-2 │   ...   │Worker-N │
    │Harbor   │         │Harbor   │         │Harbor   │
    │+Docker  │         │+Docker  │         │+Docker  │
    └───┬─────┘         └────┬────┘         └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                      ┌──────▼──────┐
                      │ NFS Storage │
                      │Shared Jobs  │
                      └─────────────┘
```

## Quick Start

### Local Development

1. **Backend:**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your settings
   pip install -r requirements.txt
   ./run.sh
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Worker (optional for local testing):**
   ```bash
   cd backend
   ./start_worker.sh 5  # Start with concurrency=5
   ```

### Production Deployment (600 Concurrent Jobs)

**See detailed guides:**
- 📘 **[QUICK_START.md](QUICK_START.md)** - Condensed deployment guide (5 steps)
- 📗 **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- 📙 **[SCALING_GUIDE.md](SCALING_GUIDE.md)** - Architecture deep-dive

**Quick deployment:**
```bash
# 1. Set up NFS server
sudo ./backend/deployment/setup_nfs_server.sh

# 2. Deploy workers (on each of 10 EC2 instances)
./backend/deployment/setup_worker.sh <POSTGRES_IP> <REDIS_IP> <OPENROUTER_KEY> 60
sudo ./backend/deployment/install_worker_service.sh 60

# 3. Verify
./backend/deployment/health_check.sh
```

## Documentation

| Document | Description |
|----------|-------------|
| [QUICK_START.md](QUICK_START.md) | Fast deployment guide (5 steps) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Full deployment instructions with troubleshooting |
| [SCALING_GUIDE.md](SCALING_GUIDE.md) | Architecture and scaling explanation |
| [SCALING_IMPLEMENTATION_SUMMARY.md](SCALING_IMPLEMENTATION_SUMMARY.md) | Implementation details and changes |
| [backend/deployment/README.md](backend/deployment/README.md) | Deployment scripts documentation |

## Technology Stack

### Frontend
- **Framework:** Next.js 16 (App Router)
- **Language:** TypeScript
- **UI:** React 19 + Tailwind CSS v4
- **Real-time:** Server-Sent Events (SSE)

### Backend
- **Framework:** FastAPI (async Python)
- **Database:** PostgreSQL + SQLAlchemy
- **Task Queue:** Celery + Redis
- **Harbor:** Terminal-Bench 2 CLI
- **Containerization:** Docker (for Harbor tasks)

### Infrastructure
- **Workers:** Celery workers on EC2 instances
- **Storage:** NFS for shared job files
- **Scaling:** Horizontal (add more workers)

## Key Features

### Upload & Configuration
- Upload single or multiple `.zip` files (Terminal-Bench tasks)
- Choose harness: Harbor (TB2) or Terminus (TB1) *[Terminus in progress]*
- Select model: GPT-4o, Claude Sonnet 3.5, etc. (via OpenRouter)
- Configure runs: 1-100 runs per task

### Execution
- Tasks queued to Redis
- Distributed across worker pool via Celery
- Each worker runs Harbor locally with Docker
- Results written to shared NFS storage
- Database updated with test results

### Monitoring
- Jobs dashboard with real-time updates
- Individual run tracking
- Pass/fail statistics
- Live log streaming via SSE
- Worker health monitoring

### Scalability
- **Current capacity:** 10 workers × 60 = 600 concurrent jobs
- **Scaling:** Add more workers to increase capacity
- **Fault tolerance:** Workers are stateless and redundant
- **Performance:** Harbor jobs run in parallel across worker pool

## Project Structure

```
tbench-harbor-runner/
├── frontend/                   # Next.js frontend
│   ├── app/                   # App router pages
│   ├── components/            # React components
│   └── lib/                   # API client
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── db/               # Database models
│   │   ├── services/         # Business logic
│   │   └── models/           # Pydantic schemas
│   ├── workers/              # Celery workers
│   ├── deployment/           # Deployment scripts
│   │   ├── setup_nfs_server.sh
│   │   ├── setup_nfs_client.sh
│   │   ├── setup_worker.sh
│   │   ├── install_worker_service.sh
│   │   └── health_check.sh
│   ├── .env                  # Backend config
│   ├── .env.worker.example   # Worker config template
│   ├── run.sh                # Start backend API
│   └── start_worker.sh       # Start Celery worker
├── DEPLOYMENT.md             # Full deployment guide
├── QUICK_START.md            # Quick deployment guide
├── SCALING_GUIDE.md          # Scaling architecture
└── README.md                 # This file
```

## Development

### Backend API

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
./run.sh

# Or manually
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
npm start
```

### Worker

```bash
cd backend

# Start worker with custom concurrency
./start_worker.sh 10  # 10 concurrent jobs

# Or manually
celery -A workers.harbor_worker worker --loglevel=info --concurrency=10
```

## Testing

### Upload a Test Task

1. Download example task from [Terminal-Bench 2 repo](https://github.com/laude-institute/terminal-bench-2)
2. Zip the task directory
3. Upload via frontend at `http://localhost:3000`
4. Monitor execution on jobs dashboard

### Load Testing

```bash
# Test with multiple concurrent tasks
# Upload 10-100 tasks simultaneously via frontend
# Monitor worker logs and Redis queue

# Check worker status
celery -A workers.harbor_worker inspect active

# Check queue length
redis-cli llen celery
```

## Configuration

### Environment Variables

**Backend API (`.env`):**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tbench
REDIS_URL=redis://localhost:6379/0
DEFAULT_OPENROUTER_KEY=sk-or-v1-xxx
JOBS_DIR=/shared/harbor-jobs/jobs
UPLOADS_DIR=/shared/harbor-jobs/uploads
```

**Worker (`.env` on worker machines):**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@<POSTGRES_IP>:5432/tbench
REDIS_URL=redis://<REDIS_IP>:6379/0
DEFAULT_OPENROUTER_KEY=sk-or-v1-xxx
JOBS_DIR=/shared/harbor-jobs/jobs
```

**Frontend (`.env`):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Monitoring

### Worker Health

```bash
# Run health check
./backend/deployment/health_check.sh

# Check worker status
sudo systemctl status harbor-worker

# View logs
sudo journalctl -u harbor-worker -f
```

### Celery Monitoring

```bash
# List all workers
celery -A workers.harbor_worker inspect ping

# View active tasks
celery -A workers.harbor_worker inspect active

# Worker statistics
celery -A workers.harbor_worker inspect stats
```

### Redis Queue

```bash
# Queue length
redis-cli llen celery

# View queued tasks
redis-cli lrange celery 0 10
```

## Troubleshooting

See [DEPLOYMENT.md](DEPLOYMENT.md#troubleshooting) for comprehensive troubleshooting guide.

**Common issues:**

- **Worker won't start:** Check logs with `sudo journalctl -u harbor-worker -n 100`
- **NFS issues:** Verify mount with `df -h | grep /shared/harbor-jobs`
- **Database connection:** Test with `psql -h <DB_IP> -U postgres -d tbench`
- **Redis connection:** Test with `redis-cli -h <REDIS_IP> ping`

## Performance

### Benchmarks

- **Single task:** 2-10 minutes (depends on task complexity)
- **100 concurrent tasks:** All start immediately
- **600 concurrent tasks:** Full worker capacity
- **1000+ tasks:** Queued and processed in batches

### Optimization

- Tune PostgreSQL connection pool
- Use async NFS options
- Optimize Harbor timeout multiplier
- Monitor and adjust worker concurrency

## Cost Estimates

**AWS (US-East, on-demand):**
- 10× t3.2xlarge workers: ~$2,400/month
- Infrastructure (DB, Redis, NFS): ~$100/month
- **Total:** ~$2,500/month

**With optimizations:**
- Spot instances for workers: ~$700/month (70% savings)
- Auto-scaling: Variable based on load
- **Optimized:** ~$800-1,200/month

See [DEPLOYMENT.md](DEPLOYMENT.md#cost-optimization) for details.

## Contributing

This is a private project. For internal development:

1. Create feature branch
2. Make changes
3. Test locally
4. Submit PR for review

## License

Private/Internal Use

## Support

For issues or questions:
1. Check documentation (DEPLOYMENT.md, QUICK_START.md)
2. Review logs (worker, backend, frontend)
3. Run health check script
4. Contact development team

## Roadmap

- [x] Core functionality (upload, run, view results)
- [x] Distributed worker architecture
- [x] Real-time log streaming
- [x] Batch upload support
- [x] Multi-model support via OpenRouter
- [ ] Terminus harness support (Terminal-Bench 1)
- [ ] Multi-language test support (Go, Rust)
- [ ] TB1 → TB2 conversion script
- [ ] Auto-scaling based on queue length
- [ ] Advanced monitoring (Grafana, CloudWatch)
- [ ] Cost analytics and optimization
- [ ] API rate limiting
- [ ] User authentication

## Acknowledgments

Built on top of:
- [Terminal-Bench](https://www.tbench.ai/) - AI agent benchmark
- [Harbor](https://github.com/laude-institute/harbor) - Terminal-Bench 2 harness
- [OpenRouter](https://openrouter.ai/) - LLM API gateway

---

**Ready to scale to 600 concurrent jobs!** 🚀

For deployment, start with [QUICK_START.md](QUICK_START.md).
