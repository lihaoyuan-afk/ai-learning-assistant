from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api import routes_chat, routes_documents, routes_profile, routes_quiz, routes_search, routes_summary
from app.core.config import settings

_bearer = HTTPBearer(auto_error=False)


async def _verify_demo(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """Require Authorization: Bearer <DEMO_PASSWORD> when DEMO_PASSWORD is set."""
    if not settings.demo_password:
        return
    if credentials is None or credentials.credentials != settings.demo_password:
        raise HTTPException(status_code=401, detail="请输入访问密码")


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
        allow_origin_regex=r"chrome-extension://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    _auth = [Depends(_verify_demo)]
    app.include_router(routes_documents.router, dependencies=_auth)
    app.include_router(routes_chat.router, dependencies=_auth)
    app.include_router(routes_summary.router, dependencies=_auth)
    app.include_router(routes_quiz.router, dependencies=_auth)
    app.include_router(routes_profile.router, dependencies=_auth)
    app.include_router(routes_search.router, dependencies=_auth)
    return app


app = create_app()
