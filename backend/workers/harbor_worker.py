from celery import Celery
from app.services.harbor_service import HarborService
from app.db.database import AsyncSessionLocal
from app.db.models import Run, Job
from app.models.schemas import JobStatus, ModelType
from pathlib import Path
from datetime import datetime
import os
import asyncio
from app.config import settings

celery_app = Celery(
    'harbor_worker',
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Important for concurrent runs
    task_acks_late=True,
    worker_max_tasks_per_child=50,  # Prevent memory leaks
    task_track_started=True,
)

@celery_app.task(bind=True, max_retries=3)
def run_harbor_task(
    self,
    job_id: str,
    run_id: str,
    run_number: int,
    task_path: str,
    output_dir: str,
    model: str,
    openrouter_key: str
):
    """Celery task to run a single Harbor execution"""
    
    async def run_async_task():
        """Run all async operations in a single event loop"""
        async def update_run_status(status: JobStatus, **kwargs):
            async with AsyncSessionLocal() as session:
                run = await session.get(Run, run_id)
                if run:
                    run.status = status
                    for key, value in kwargs.items():
                        setattr(run, key, value)
                    await session.commit()
        
        try:
            # Update status to running
            await update_run_status(
                JobStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            
            # Initialize Harbor service
            harbor_service = HarborService(openrouter_key)
            
            # Convert model string to ModelType enum
            model_enum = ModelType(model)
            
            # Run Harbor task
            result = await harbor_service.run_task(
                task_path=Path(task_path),
                output_dir=Path(output_dir),
                run_number=run_number,
                model=model_enum,
            )
            
            # Update database with results
            await update_run_status(
                JobStatus.COMPLETED if result["status"] == "completed" else JobStatus.FAILED,
                tests_passed=result.get("tests_passed", 0),
                tests_total=result.get("tests_total", 0),
                logs=result.get("logs", ""),
                result_path=result.get("result_path"),
                error=result.get("error"),
                completed_at=datetime.utcnow()
            )
            
            # Update job status if all runs are done
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                runs = await session.execute(
                    select(Run).where(Run.job_id == job_id)
                )
                all_runs = list(runs.scalars().all())
                
                if all(run.status in [JobStatus.COMPLETED, JobStatus.FAILED] for run in all_runs):
                    job = await session.get(Job, job_id)
                    if job:
                        job.status = JobStatus.COMPLETED
                        job.completed_at = datetime.utcnow()
                        await session.commit()
            
            return result
            
        except Exception as exc:
            # Update status to failed
            await update_run_status(
                JobStatus.FAILED,
                error=str(exc),
                completed_at=datetime.utcnow()
            )
            raise
    
    # Run all async operations in a single event loop
    try:
        result = asyncio.run(run_async_task())
        return result
    except Exception as exc:
        # Retry logic
        raise self.retry(exc=exc, countdown=60)

