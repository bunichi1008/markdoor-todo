from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UTCDateTime, utc_now


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("length(title) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 5000", name="description_length"
        ),
        Index("ix_tasks_created_at_id", "created_at", "id"),
        Index("ix_tasks_completed_created_at_id", "completed", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
