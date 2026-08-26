from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class every ORM model inherits from.

    SQLAlchemy uses this to collect table metadata (via `Base.metadata`) so
    Alembic can compare it against the live database and generate migrations.
    """
