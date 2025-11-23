from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings
from app.db.models import Base

# Create async engine with proper pool settings for Celery workers
# Note: pool_pre_ping is disabled because it conflicts with asyncio.run() creating new event loops
# Connections are reset on return to pool instead
engine = create_async_engine(
    settings.database_url,
    echo=True,  # Set to False in production
    future=True,
    pool_size=10,  # Increase pool size for concurrent workers
    max_overflow=20,  # Allow overflow connections
    pool_pre_ping=False,  # Disabled - conflicts with multiple event loops from asyncio.run()
    pool_reset_on_return='commit',  # Reset connections when returned to pool
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Dependency to get DB session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Initialize database (create tables)
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

