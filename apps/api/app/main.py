from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_chat, routes_documents, routes_profile, routes_quiz, routes_search, routes_summary
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.session import create_tables, db_session
    from app.models.document import Document
    from app.schemas.document import DocumentStatus

    create_tables()

    # Any document stuck in uploaded/processing means the previous process was
    # killed while a background task was running.  Mark them failed so the user
    # can re-upload rather than waiting forever.
    with db_session() as db:
        stuck = (
            db.query(Document)
            .filter(Document.status.in_(["uploaded", "processing"]))
            .all()
        )
        for doc in stuck:
            doc.status = DocumentStatus.failed.value

    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    app.include_router(routes_documents.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_summary.router)
    app.include_router(routes_quiz.router)
    app.include_router(routes_profile.router)
    app.include_router(routes_search.router)
    return app


app = create_app()
