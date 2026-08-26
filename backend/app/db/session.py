from collections.abc import Callable, Generator
from contextlib import contextmanager

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


@contextmanager
def session_scope(session_factory: Callable[[], Session] = SessionLocal) -> Generator[Session, None, None]:
    """One database session for one unit of work, for code that isn't a
    FastAPI request/websocket handler (e.g. the background poller) and so
    can't use `get_db` via `Depends`.

    Takes the session factory as a parameter (defaulting to the real
    `SessionLocal`) so tests can pass a factory bound to an in-memory SQLite
    engine instead, without this function needing to know that's happening.
    """
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
