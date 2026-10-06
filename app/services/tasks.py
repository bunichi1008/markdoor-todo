from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskCreate, TaskUpdate


class TaskNotFound(Exception):
    pass


def get_task(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise TaskNotFound
    return task


def create_task(session: Session, payload: TaskCreate) -> Task:
    task = Task(**payload.model_dump())
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def update_task(session: Session, task_id: int, payload: TaskUpdate) -> Task:
    task = get_task(session, task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    session.commit()
    session.refresh(task)
    return task


def list_tasks(session: Session, completed: bool | None, limit: int, offset: int):
    filters = [] if completed is None else [Task.completed == completed]
    total = session.scalar(select(func.count()).select_from(Task).where(*filters))
    items = session.scalars(
        select(Task)
        .where(*filters)
        .order_by(Task.created_at.desc(), Task.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def delete_task(session: Session, task_id: int) -> None:
    task = get_task(session, task_id)
    session.delete(task)
    session.commit()
