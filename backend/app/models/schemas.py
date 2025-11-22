from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class HarnessType(str, Enum):
    HARBOR = "harbor"
    TERMINUS = "terminus"

class ModelType(str, Enum):
    GPT_4O = "openai/gpt-4o"
    CLAUDE_35_SONNET = "anthropic/claude-3.5-sonnet"
    GEMINI_PRO = "google/gemini-pro-1.5"
    LLAMA_405B = "meta-llama/llama-3.1-405b-instruct"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class RunResponse(BaseModel):
    id: str
    job_id: str
    run_number: int
    status: JobStatus
    tests_passed: Optional[int] = None
    tests_total: Optional[int] = None
    logs: Optional[str] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

class JobResponse(BaseModel):
    id: str
    task_name: str
    status: JobStatus
    harness: str
    model: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    runs: List[RunResponse] = []

class UploadResponse(BaseModel):
    job_id: str
    status: str
    runs_queued: int
    message: str

