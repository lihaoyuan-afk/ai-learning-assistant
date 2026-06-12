from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_auth, routes_chat, routes_documents, routes_profile, routes_quiz, routes_search, routes_summary, routes_tts
from app.api.deps import CurrentUserID, _resolve_user_id  # noqa: F401 — re-exported for convenience
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.session import create_tables, db_session, engine
    from app.models import document, learning_memory, user  # ensure all models imported
    from app.models.document import Document
    from app.schemas.document import DocumentStatus

    create_tables()
    _run_column_migrations(engine)

    # Reset stuck documents
    with db_session() as db:
        stuck = (
            db.query(Document)
            .filter(Document.status.in_(["uploaded", "processing"]))
            .all()
        )
        for doc in stuck:
            doc.status = DocumentStatus.failed.value

    yield


def _run_column_migrations(engine) -> None:
    """Add columns that were introduced after the initial DB creation."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for table, column, col_def in [
            ("documents", "user_id", "TEXT"),
            ("documents", "is_public", "INTEGER DEFAULT 0"),
            ("documents", "forked_from", "TEXT"),
            ("learning_memory", "user_id", "TEXT"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
                conn.commit()
            except Exception:
                pass  # column already exists


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"chrome-extension://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    # Auth routes are PUBLIC (no auth required)
    app.include_router(routes_auth.router)

    # All other routes require auth (JWT or demo password)
    from app.api.deps import _resolve_user_id as _ruid
    _auth = [Depends(_ruid)]
    app.include_router(routes_documents.router, dependencies=_auth)
    app.include_router(routes_chat.router, dependencies=_auth)
    app.include_router(routes_summary.router, dependencies=_auth)
    app.include_router(routes_quiz.router, dependencies=_auth)
    app.include_router(routes_profile.router, dependencies=_auth)
    app.include_router(routes_search.router, dependencies=_auth)
    app.include_router(routes_tts.router, dependencies=_auth)
    return app


app = create_app()
