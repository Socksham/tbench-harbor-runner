from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pathlib import Path
import asyncio
import json
from app.config import settings

router = APIRouter()

@router.get("/{job_id}/runs/{run_number}/logs/stream")
async def stream_run_logs(job_id: str, run_number: int):
    """Stream logs for a specific run using Server-Sent Events"""
    
    async def event_generator():
        job_dir = Path(settings.jobs_dir) / job_id
        
        # Try multiple possible log locations
        log_paths = [
            job_dir / f"run_{run_number}" / "trial.log",
            job_dir / f"run_{run_number}" / "agent" / "oracle.txt",
            job_dir / f"run_{run_number}" / "exception.txt",
        ]
        
        last_positions = {str(p): 0 for p in log_paths}
        found_log = False
        
        while True:
            for log_path in log_paths:
                if log_path.exists():
                    found_log = True
                    try:
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            f.seek(last_positions[str(log_path)])
                            new_content = f.read()
                            last_positions[str(log_path)] = f.tell()
                            
                            if new_content:
                                yield f"data: {json.dumps({'logs': new_content, 'source': log_path.name})}\n\n"
                    except Exception as e:
                        yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            # Check if we should stop (you might want to check DB status here)
            # For now, we'll just keep streaming until connection closes
            
            if not found_log:
                # Wait a bit before checking again
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(0.5)  # Poll every 500ms
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )

