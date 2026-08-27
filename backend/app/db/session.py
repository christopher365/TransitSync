from collections.abc import Callable, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def normalize_database_url(url: str) -> str:
    """Every Postgres host/tool hands you a bare `postgresql://` URL — but
    SQLAlchemy defaults that scheme to the psycopg2 driver, which isn't
    installed in this project (only psycopg, v3, is). Without this, pasting
    a connection string exactly as a host gives it crashes the app at
    startup with "No module named 'psycopg2'" — a real failure this project
    hit deploying against Neon. Rewriting the scheme here means the app
    just works with the connection string as given, instead of requiring
    everyone who configures it to remember an easy-to-miss edit.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)

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
