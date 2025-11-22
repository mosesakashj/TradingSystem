# Database Configuration and Session Management
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator

from .models import Base


class DatabaseConfig:
    """Database configuration"""
    
    def __init__(self):
        self.DATABASE_URL = os.getenv(
            'DATABASE_URL',
            'postgresql://trading_user:trading_pass@localhost:5432/trading_db'
        )
        
        # Connection pool settings
        self.POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))
        self.MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))
        self.POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))
        
        # Echo SQL (disable in production)
        self.ECHO_SQL = os.getenv('DB_ECHO_SQL', 'false').lower() == 'true'


# Global configuration
config = DatabaseConfig()

# Create engine with connection pooling
engine = create_engine(
    config.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=config.POOL_SIZE,
    max_overflow=config.MAX_OVERFLOW,
    pool_timeout=config.POOL_TIMEOUT,
    pool_recycle=config.POOL_RECYCLE,
    echo=config.ECHO_SQL,
    future=True  # SQLAlchemy 2.0 style
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def drop_db():
    """Drop all tables - USE WITH CAUTION"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Database session context manager for dependency injection
    
    Usage:
        with get_db() as db:
            db.query(Signal).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Get database session for FastAPI dependency injection
    
    Usage in FastAPI:
        @app.get("/signals")
        def get_signals(db: Session = Depends(get_db_session)):
            return db.query(Signal).all()
    """
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # FastAPI will handle closing


# Health check
def check_database_health() -> dict:
    """Check database connectivity and latency"""
    import time
    
    try:
        start = time.time()
        with get_db() as db:
            db.execute("SELECT 1")
        latency_ms = (time.time() - start) * 1000
        
        return {
            "healthy": True,
            "latency_ms": round(latency_ms, 2)
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }
