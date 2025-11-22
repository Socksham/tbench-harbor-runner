from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.db.database import init_db
from app.api import upload, jobs, logs

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing database...")
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(logs.router, prefix="/api/jobs", tags=["logs"])

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Terminal-Bench Harbor Runner API",
        "version": settings.api_version
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

