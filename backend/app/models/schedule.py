from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleRun(SQLModel, table=True):
    """One execution of the scheduler. History is retained so results can be compared."""

    __tablename__ = "schedule_run"

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=_utcnow)
    notes: str | None = None


class ScheduledAssignment(SQLModel, table=True):
    """Output row: one piece of work produced by a scheduler run. A single Task may
    yield multiple assignments when the scheduler splits it across machine gaps."""

    __tablename__ = "scheduled_assignment"

    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="schedule_run.id", index=True)
    task_id: int = Field(foreign_key="task.id", index=True)
    split_index: int = Field(default=0)
    assigned_quantity: float
    start_time: datetime
    end_time: datetime
