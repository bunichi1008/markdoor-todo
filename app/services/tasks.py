from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskCreate


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
