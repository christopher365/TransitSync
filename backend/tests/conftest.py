import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


@pytest.fixture()
def db_session() -> Session:
    """An isolated in-memory SQLite session, fresh for every test.

    We don't need a real PostgreSQL instance to test repository logic: the
    Repository pattern means our test code talks to the same interface
    (`StopRepositoryInterface`) regardless of which database sits behind it.
    SQLite in-memory is fast and needs no setup, which is exactly what a
    unit test should be.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
