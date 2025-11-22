from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from app.models.schemas import JobStatus

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True)
    task_name = Column(String, nullable=False, index=True)
    task_path = Column(String, nullable=False)
    harness = Column(String, nullable=False)  # 'harbor' or 'terminus'
    model = Column(String, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

class Run(Base):
    __tablename__ = "runs"
    
    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, nullable=False, index=True)
    run_number = Column(Integer, nullable=False)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    tests_passed = Column(Integer, nullable=True)
    tests_total = Column(Integer, nullable=True)
    logs = Column(Text, nullable=True)
    result_path = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

