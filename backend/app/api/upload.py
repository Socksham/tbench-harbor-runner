from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import tempfile
import shutil
from app.db.database import get_db
from app.services.task_extractor import extract_and_validate_task, extract_task_name
from app.services.job_manager import create_job_and_queue_runs
from app.models.schemas import HarnessType, ModelType, UploadResponse

router = APIRouter()

@router.post("/", response_model=UploadResponse)
async def upload_task(
    file: UploadFile = File(...),
    harness: HarnessType = Form(...),
    model: ModelType = Form(...),
    openrouter_key: str = Form(...),
    n_runs: int = Form(10),
    db: AsyncSession = Depends(get_db)
):
    """Upload a zipped Terminal-Bench task and queue N runs"""
    
    if not file.filename or not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a .zip file")
    
    if n_runs < 1 or n_runs > 100:
        raise HTTPException(status_code=400, detail="n_runs must be between 1 and 100")
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / file.filename
        
        # Save uploaded file
        with open(zip_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Extract and validate task structure
            task_path = await extract_and_validate_task(zip_path, temp_path, harness)
            task_name = extract_task_name(task_path)
            
            # Create job and queue runs
            job = await create_job_and_queue_runs(
                session=db,
                task_path=task_path,
                task_name=task_name,
                harness=harness,
                model=model,
                openrouter_key=openrouter_key,
                n_runs=n_runs
            )
            
            return UploadResponse(
                job_id=job.id,
                status="queued",
                runs_queued=n_runs,
                message=f"Task '{task_name}' uploaded successfully. {n_runs} runs queued."
            )
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing task: {str(e)}")

