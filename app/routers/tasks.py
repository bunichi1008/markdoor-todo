from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import TaskCreate, TaskRead, TaskUpdate
from app.services import tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, session: DatabaseSession):
    return tasks.create_task(session, payload)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: DatabaseSession):
    return tasks.get_task(session, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, session: DatabaseSession):
    return tasks.update_task(session, task_id, payload)
