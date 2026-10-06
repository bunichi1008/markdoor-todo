from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, StringConstraints(max_length=5000)]


class TaskInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TaskCreate(TaskInput):
    title: Title
    description: Description | None = None
    completed: bool = False


class TaskUpdate(TaskInput):
    # Defaults represent omission only; explicit null still fails the non-nullable types.
    title: Title = Field(default=None)
    description: Description | None = None
    completed: bool = Field(default=None)

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("更新する項目を指定してください。")
        return self


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    updated_at: datetime


class TaskPage(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int
