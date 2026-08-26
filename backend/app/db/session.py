from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields one database session per request.

    The `try`/`finally` guarantees the session is closed even if the request
    handler raises an exception, so connections don't leak under errors.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
