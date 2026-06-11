from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_url(raw: str) -> str:
    """Neon/Supabase hand out postgresql:// URLs; psycopg3 needs postgresql+psycopg://."""
    if raw.startswith("postgresql://") or raw.startswith("postgres://"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1).replace(
            "postgres://", "postgresql+psycopg://", 1
        )
    return raw


_url = _build_url(settings.database_url)
_connect_args = {"check_same_thread": False} if "sqlite" in _url else {}

engine = create_engine(_url, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    import app.models  # noqa: F401 — registers all ORM models in metadata
    from app.models.base import Base

    Base.metadata.create_all(bind=engine)
