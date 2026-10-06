from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import TaskCreate, TaskPage, TaskRead, TaskUpdate
from app.services import tasks

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskCreate, session: DatabaseSession):
    return tasks.create_task(session, payload)


@router.get("", response_model=TaskPage)
def list_tasks(
    session: DatabaseSession,
    completed: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return tasks.list_tasks(session, completed, limit, offset)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: DatabaseSession):
    return tasks.get_task(session, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, payload: TaskUpdate, session: DatabaseSession):
    return tasks.update_task(session, task_id, payload)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, session: DatabaseSession):
    tasks.delete_task(session, task_id)
    return Response(status_code=204)
