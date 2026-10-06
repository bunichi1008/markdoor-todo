import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import models  # noqa: F401 - register tables before create_all
from app.db import Base, create_database
from app.routers.tasks import router
from app.services.tasks import TaskNotFound

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'data' / 'tasks.sqlite3'}"


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

    return application


app = create_app()
