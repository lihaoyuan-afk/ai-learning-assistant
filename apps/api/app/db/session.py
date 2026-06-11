from contextlib import contextmanager
from typing import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _build_url(raw: str) -> str:
    """Normalize postgresql:// to postgresql+psycopg:// and strip pooler-incompatible params."""
    if raw.startswith("postgresql://") or raw.startswith("postgres://"):
        url = raw.replace("postgresql://", "postgresql+psycopg://", 1).replace(
            "postgres://", "postgresql+psycopg://", 1
        )
        parsed = urlparse(url)
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items() if k != "channel_binding"}
        return urlunparse(parsed._replace(query=urlencode(qs)))
    return raw


_url = _build_url(settings.database_url)
_is_sqlite = "sqlite" in _url
_connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(_url, connect_args=_connect_args, pool_pre_ping=not _is_sqlite)
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
