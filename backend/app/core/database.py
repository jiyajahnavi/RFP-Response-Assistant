import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings

logger = logging.getLogger("rfp_assistant.database")

Base = declarative_base()

# Configure engine arguments based on dialect
connect_args = {}
engine_kwargs = {
    "echo": settings.DB_ECHO,
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # Memory or local file db configuration
    if ":memory:" in settings.DATABASE_URL:
        engine_kwargs["poolclass"] = StaticPool
else:
    # SQL Server / Azure SQL / PostgreSQL connection pooling settings
    engine_kwargs.update(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_pre_ping": True,
        }
    )

try:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        **engine_kwargs,
    )
    logger.info("Database engine initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize database engine: %s", str(e))
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI routes.
    Ensures safe session lifecycle management and clean closure.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as exc:
        logger.error("Database session error: %s", str(exc))
        db.rollback()
        raise
    finally:
        db.close()
