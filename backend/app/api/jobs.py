from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.job_manager import get_job, get_runs
from app.models.schemas import JobResponse, RunResponse

router = APIRouter()

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get job status and all run results"""
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    runs = await get_runs(db, job_id)
    
    return JobResponse(
        id=job.id,
        task_name=job.task_name,
        status=job.status,
        harness=job.harness,
        model=job.model,
        created_at=job.created_at,
        completed_at=job.completed_at,
        runs=[RunResponse(
            id=run.id,
            job_id=run.job_id,
            run_number=run.run_number,
            status=run.status,
            tests_passed=run.tests_passed,
            tests_total=run.tests_total,
            logs=run.logs,
            result_path=run.result_path,
            error=run.error,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at
        ) for run in runs]
    )

