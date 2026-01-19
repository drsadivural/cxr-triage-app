"""
Database connection and session management.
"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.config import settings, AppSettings, get_secret_manager
from app.models import Base, AppConfig


# Default database URL from environment
DEFAULT_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://cxr_user:cxr_password@db:5432/cxr_triage"
)

# Async engine for FastAPI
async_engine = None
AsyncSessionLocal = None

# Sync engine for migrations and Celery
sync_engine = None
SyncSessionLocal = None


def init_database(database_url: str = None, async_url: str = None):
    """Initialize database connections."""
    global async_engine, AsyncSessionLocal, sync_engine, SyncSessionLocal
    
    if async_url is None:
        async_url = database_url or DEFAULT_DATABASE_URL
    
    # Convert async URL to sync URL for migrations
    sync_url = async_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    
    # Create async engine
    async_engine = create_async_engine(
        async_url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    AsyncSessionLocal = async_sessionmaker(
        async_engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    # Create sync engine
    sync_engine = create_engine(
        sync_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    SyncSessionLocal = sessionmaker(bind=sync_engine)


def get_sync_session():
    """Get synchronous database session."""
    if SyncSessionLocal is None:
        init_database()
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    if AsyncSessionLocal is None:
        init_database()
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    if async_engine is None:
        init_database()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def create_tables_sync():
    """Create all database tables synchronously."""
    if sync_engine is None:
        init_database()
    Base.metadata.create_all(bind=sync_engine)


async def test_connection() -> bool:
    """Test database connection."""
    try:
        if async_engine is None:
            init_database()
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False


# Settings persistence functions
async def load_app_settings(db: AsyncSession) -> AppSettings:
    """Load application settings from database."""
    from sqlalchemy import select
    
    try:
        result = await db.execute(
            select(AppConfig).where(AppConfig.config_key == "app_settings")
        )
        config = result.scalar_one_or_none()
        
        if config is None:
            return AppSettings()
        
        try:
            secret_manager = get_secret_manager()
            return secret_manager.decrypt_settings(config.encrypted_value)
        except Exception as e:
            print(f"Failed to decrypt settings: {e}")
            return AppSettings()
    except Exception as e:
        print(f"Failed to load settings from database: {e}")
        return AppSettings()


async def save_app_settings(db: AsyncSession, app_settings: AppSettings):
    """Save application settings to database."""
    from sqlalchemy import select
    
    secret_manager = get_secret_manager()
    encrypted = secret_manager.encrypt_settings(app_settings)
    
    result = await db.execute(
        select(AppConfig).where(AppConfig.config_key == "app_settings")
    )
    config = result.scalar_one_or_none()
    
    if config is None:
        config = AppConfig(config_key="app_settings", encrypted_value=encrypted)
        db.add(config)
    else:
        config.encrypted_value = encrypted
    
    await db.commit()


# Initialize on module load with default settings
init_database()
