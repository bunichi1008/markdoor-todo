import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401 - register tables before create_all
from app.db import Base, create_database
from app.routers.tasks import router
from app.services.tasks import TaskNotFound

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'tasks.sqlite3'}"
logger = logging.getLogger(__name__)


def create_app(database_url: str | None = None) -> FastAPI:
    engine, session_factory = create_database(
        database_url or os.getenv("TASKS_DATABASE_URL", DEFAULT_DATABASE_URL)
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        try:
            Base.metadata.create_all(engine)
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Markdoor TODO", lifespan=lifespan)
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.include_router(router)

    @application.exception_handler(TaskNotFound)
    async def not_found(request, exc):
        return JSONResponse(status_code=404, content={"detail": "タスクが見つかりません。"})

    @application.exception_handler(Exception)
    @application.exception_handler(SQLAlchemyError)
    async def internal_error(request, exc):
        logger.error("Request failed: %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "処理に失敗しました。時間をおいて再試行してください。"},
        )

    return application


app = create_app()
