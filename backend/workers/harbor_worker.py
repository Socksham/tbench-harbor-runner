from celery import Celery
from app.services.harbor_service import HarborService
from app.db.database_sync import SyncSessionLocal
from app.db.models import Run, Job
from app.models.schemas import JobStatus, ModelType
from pathlib import Path
from datetime import datetime
import asyncio
from app.config import settings
from sqlalchemy import select

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
    
    def update_run_status(status: JobStatus, **kwargs):
        """Update run status using sync database"""
        with SyncSessionLocal() as session:
            try:
                run = session.get(Run, run_id)
                if run:
                    run.status = status
                    for key, value in kwargs.items():
                        setattr(run, key, value)
                    session.commit()
            except Exception as e:
                session.rollback()
                raise
    
    async def run_harbor_async():
        """Run Harbor service (needs async for subprocess)"""
        harbor_service = HarborService(openrouter_key)
        model_enum = ModelType(model)
        
        result = await harbor_service.run_task(
            task_path=Path(task_path),
            output_dir=Path(output_dir),
            run_number=run_number,
            model=model_enum,
        )
        return result
    
    try:
        # Update status to running (sync DB - no event loop issues!)
        update_run_status(
            JobStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Update job status to RUNNING if it's still PENDING (when first run starts)
        with SyncSessionLocal() as session:
            try:
                job = session.get(Job, job_id)
                if job and job.status == JobStatus.PENDING:
                    job.status = JobStatus.RUNNING
                    session.commit()
            except Exception as e:
                session.rollback()
                # Don't fail the task if job status update fails
                pass
        
        # Run Harbor task (needs async for subprocess management)
        result = asyncio.run(run_harbor_async())
        
        # Update database with results (sync DB)
        update_run_status(
            JobStatus.COMPLETED if result["status"] == "completed" else JobStatus.FAILED,
            tests_passed=result.get("tests_passed", 0),
            tests_total=result.get("tests_total", 0),
            logs=result.get("logs", ""),
            result_path=result.get("result_path"),
            error=result.get("error"),
            completed_at=datetime.utcnow()
        )
        
        # Update job status if all runs are done (sync DB)
        # Use retry logic with exponential backoff to handle concurrent updates
        max_retries = 3
        for attempt in range(max_retries):
            with SyncSessionLocal() as session:
                try:
                    runs = session.execute(
                        select(Run).where(Run.job_id == job_id)
                    )
                    all_runs = list(runs.scalars().all())
                    
                    if all(run.status in [JobStatus.COMPLETED, JobStatus.FAILED] for run in all_runs):
                        job = session.get(Job, job_id)
                        if job and job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
                            job.status = JobStatus.COMPLETED
                            job.completed_at = datetime.utcnow()
                            session.commit()
                            break  # Success, exit retry loop
                        else:
                            # Job already updated by another worker, no need to retry
                            session.commit()
                            break
                    else:
                        # Not all runs complete yet, no update needed
                        session.commit()
                        break
                except Exception as e:
                    session.rollback()
                    if attempt == max_retries - 1:
                        # Last attempt failed, log but don't raise (another worker may have succeeded)
                        print(f"Failed to update job status after {max_retries} attempts: {e}")
                    else:
                        import time
                        time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
        
        return result
        
    except Exception as exc:
        # Update status to failed (sync DB)
        try:
            error_msg = str(exc)
            # Truncate long errors to prevent database issues
            if len(error_msg) > 10000:
                error_msg = error_msg[:10000] + "... (truncated)"
            
            update_run_status(
                JobStatus.FAILED,
                error=error_msg,
                completed_at=datetime.utcnow()
            )
        except Exception as db_error:
            # Log but don't fail if we can't update status
            print(f"Failed to update run status: {db_error}")
            pass
        
        # Only retry on certain exceptions, not all
        if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
            raise self.retry(exc=exc, countdown=60)
        else:
            # Don't retry on configuration or validation errors
            raise
