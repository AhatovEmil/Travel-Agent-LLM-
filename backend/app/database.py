from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def _table_columns(conn, table: str) -> set[str]:
    if settings.database_url.startswith("sqlite"):
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}
    rows = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table AND table_schema = 'public'"
        ),
        {"table": table},
    ).fetchall()
    return {row[0] for row in rows}


def _add_column(conn, table: str, column: str, coltype: str) -> None:
    cols = _table_columns(conn, table)
    if column in cols:
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def ensure_schema() -> None:
    """create_all + soft ALTER for existing DBs."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _add_column(conn, "trips", "start_date", "DATE")
        _add_column(conn, "trips", "share_token", "VARCHAR(64)")
        _add_column(conn, "users", "credit_balance", "INTEGER DEFAULT 0 NOT NULL")
        _add_column(conn, "users", "free_used_month", "VARCHAR(7) DEFAULT '' NOT NULL")
        _add_column(conn, "users", "free_used_count", "INTEGER DEFAULT 0 NOT NULL")
        _add_column(conn, "users", "telegram_id", "VARCHAR(64)")
