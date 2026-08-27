from app.db.session import normalize_database_url


def test_rewrites_bare_postgresql_scheme_to_use_psycopg() -> None:
    url = "postgresql://user:pass@host/dbname?sslmode=require"

    assert normalize_database_url(url) == "postgresql+psycopg://user:pass@host/dbname?sslmode=require"


def test_leaves_an_already_explicit_driver_scheme_untouched() -> None:
    url = "postgresql+psycopg://user:pass@host/dbname"

    assert normalize_database_url(url) == url


def test_leaves_non_postgres_urls_untouched() -> None:
    url = "sqlite:///:memory:"

    assert normalize_database_url(url) == url
