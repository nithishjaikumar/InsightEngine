import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Engine configuration with connection health check and recycle for MySQL
engine_kwargs = {
    "pool_pre_ping": True,
}

# Only add pool_recycle if not sqlite (pool_recycle is standard for MySQL long-lived connections)
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional SQLAlchemy database session.
    Automatically handles transaction rollback on exception and ensures session cleanup.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception as exc:
        db.rollback()
        logger.error("Database session rolled back due to error: %s", exc)
        raise
    finally:
        db.close()
