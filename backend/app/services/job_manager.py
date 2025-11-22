from pathlib import Path
import uuid
import shutil
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Job, Run
from app.models.schemas import HarnessType, ModelType, JobStatus
from app.config import settings
from workers.harbor_worker import run_harbor_task

async def create_job_and_queue_runs(
    session: AsyncSession,
    task_path: Path,
    task_name: str,
    harness: HarnessType,
    model: ModelType,
    openrouter_key: str,
    n_runs: int = 10
) -> Job:
    """Create a job and queue all runs"""
    
    job_id = str(uuid.uuid4())
    # Use absolute path to ensure Celery workers can find it
    job_dir = settings.jobs_dir_absolute / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy task to job directory
    task_dest = job_dir / "task"
    if task_path.is_dir():
        shutil.copytree(task_path, task_dest)
    else:
        task_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(task_path, task_dest)
    
    # Resolve to absolute paths
    task_dest_abs = task_dest.resolve()
    job_dir_abs = job_dir.resolve()
    
    # Create job in database
    job = Job(
        id=job_id,
        task_name=task_name,
        task_path=str(task_dest_abs),
        harness=harness.value,
        model=model.value,
        status=JobStatus.PENDING
    )
    
    session.add(job)
    await session.flush()
    
    # Create runs in database and queue Celery tasks
    for i in range(1, n_runs + 1):
        run_id = str(uuid.uuid4())
        run = Run(
            id=run_id,
            job_id=job_id,
            run_number=i,
            status=JobStatus.PENDING
        )
        session.add(run)
        
        # Queue Celery task with absolute paths
        run_harbor_task.delay(
            job_id=job_id,
            run_id=run_id,
            run_number=i,
            task_path=str(task_dest_abs),
            output_dir=str(job_dir_abs),
            model=model.value,
            openrouter_key=openrouter_key
        )
    
    await session.commit()
    return job

async def get_job(session: AsyncSession, job_id: str) -> Job:
    """Get a job by ID"""
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()

async def get_runs(session: AsyncSession, job_id: str) -> list[Run]:
    """Get all runs for a job"""
    result = await session.execute(
        select(Run).where(Run.job_id == job_id).order_by(Run.run_number)
    )
    return list(result.scalars().all())

