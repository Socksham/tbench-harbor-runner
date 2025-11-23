from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.db.models import Base

# Convert asyncpg URL to psycopg2 URL for sync access
# postgresql+asyncpg:// -> postgresql://
sync_db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

# Create sync engine with proper pool settings
sync_engine = create_engine(
    sync_db_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Can use this with sync!
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=True,  # Set to False in production
)

# Create sync session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Dependency to get DB session (for compatibility if needed)
def get_sync_db():
    """Get a sync database session"""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

