from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from app.db.database import get_db
from app.services.job_manager import get_job, get_runs
from app.models.schemas import JobResponse, RunResponse
from app.db.models import Job

router = APIRouter()

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List all jobs with pagination"""
    result = await db.execute(
        select(Job).order_by(desc(Job.created_at)).limit(limit).offset(offset)
    )
    jobs = result.scalars().all()
    
    job_responses = []
    for job in jobs:
        runs = await get_runs(db, job.id)
        job_responses.append(JobResponse(
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
                episodes=run.episodes or [],
                agent_name=run.agent_name,
                result_path=run.result_path,
                error=run.error,
                started_at=run.started_at,
                completed_at=run.completed_at,
                created_at=run.created_at
            ) for run in runs]
        ))
    
    return job_responses

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
            episodes=run.episodes or [],
            agent_name=run.agent_name,
            result_path=run.result_path,
            error=run.error,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at
        ) for run in runs]
    )

