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


def ensure_schema() -> None:
    """create_all + soft ALTER for existing SQLite DBs."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(trips)")).fetchall()
        cols = {row[1] for row in rows}
        if "start_date" not in cols:
            conn.execute(text("ALTER TABLE trips ADD COLUMN start_date DATE"))
        if "share_token" not in cols:
            conn.execute(text("ALTER TABLE trips ADD COLUMN share_token VARCHAR(64)"))
