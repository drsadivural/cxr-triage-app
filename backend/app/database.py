"""
Database connection and session management.
"""
import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError

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

# Track if tables have been created
_tables_created = False


def init_database(database_url: str = None, async_url: str = None):
    """Initialize database connections."""
    global async_engine, AsyncSessionLocal, sync_engine, SyncSessionLocal
    
    if async_url is None:
        async_url = database_url or DEFAULT_DATABASE_URL
    
    # Convert async URL to sync URL for migrations
    sync_url = async_url.replace("+asyncpg", "").replace("+aiosqlite", "")
    
    # Create async engine with error handling
    try:
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
    except Exception as e:
        print(f"Failed to create async engine: {e}")
        async_engine = None
        AsyncSessionLocal = None
    
    # Create sync engine
    try:
        sync_engine = create_engine(
            sync_url,
            echo=settings.debug,
            pool_pre_ping=True,
        )
        SyncSessionLocal = sessionmaker(bind=sync_engine)
    except Exception as e:
        print(f"Failed to create sync engine: {e}")
        sync_engine = None
        SyncSessionLocal = None


def get_sync_session():
    """Get synchronous database session."""
    if SyncSessionLocal is None:
        init_database()
    if SyncSessionLocal is None:
        raise RuntimeError("Database not initialized")
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    if AsyncSessionLocal is None:
        init_database()
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    global _tables_created
    
    if _tables_created:
        return
    
    if async_engine is None:
        init_database()
    
    if async_engine is None:
        print("Cannot create tables: database engine not initialized")
        return
    
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True
        print("Database tables created successfully")
    except Exception as e:
        print(f"Failed to create database tables: {e}")


def create_tables_sync():
    """Create all database tables synchronously."""
    global _tables_created
    
    if _tables_created:
        return
    
    if sync_engine is None:
        init_database()
    
    if sync_engine is None:
        print("Cannot create tables: database engine not initialized")
        return
    
    try:
        Base.metadata.create_all(bind=sync_engine)
        _tables_created = True
        print("Database tables created successfully (sync)")
    except Exception as e:
        print(f"Failed to create database tables: {e}")


async def test_connection() -> bool:
    """Test database connection."""
    try:
        if async_engine is None:
            init_database()
        if async_engine is None:
            return False
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
        # Ensure tables exist
        await create_tables()
        
        result = await db.execute(
            select(AppConfig).where(AppConfig.config_key == "app_settings")
        )
        config = result.scalar_one_or_none()
        
        if config is None:
            # Return default settings if none saved
            print("No saved settings found, using defaults")
            return AppSettings()
        
        try:
            secret_manager = get_secret_manager()
            return secret_manager.decrypt_settings(config.encrypted_value)
        except Exception as e:
            print(f"Failed to decrypt settings: {e}")
            return AppSettings()
            
    except (OperationalError, ProgrammingError) as e:
        # Table doesn't exist or database error
        print(f"Database error loading settings (table may not exist): {e}")
        return AppSettings()
    except Exception as e:
        print(f"Failed to load settings from database: {e}")
        return AppSettings()


async def save_app_settings(db: AsyncSession, app_settings: AppSettings):
    """Save application settings to database."""
    from sqlalchemy import select
    
    try:
        # Ensure tables exist
        await create_tables()
        
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
        print("Settings saved successfully")
    except Exception as e:
        print(f"Failed to save settings: {e}")
        raise


# Initialize on module load with default settings
init_database()
