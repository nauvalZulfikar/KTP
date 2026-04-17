from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer


class ScheduleRunCreate(BaseModel):
    notes: str | None = None


class ScheduleRunRead(BaseModel):
    id: int
    created_at: datetime
    notes: str | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def _ser_created_at(self, v: datetime) -> str:
        # SQLite strips tzinfo; created_at is stored as UTC, so re-attach it before
        # serializing so clients know to convert to their local zone.
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()


class ScheduledAssignmentRead(BaseModel):
    id: int
    run_id: int
    task_id: int
    split_index: int
    assigned_quantity: float
    start_time: datetime
    end_time: datetime
    model_config = ConfigDict(from_attributes=True)


class ScheduleRunDetail(ScheduleRunRead):
    assignments: list[ScheduledAssignmentRead]


class MetricsRead(BaseModel):
    machine_utilization: dict[str, float]
    component_waiting_days: dict[str, float]
    product_waiting_days: dict[str, float]
    late_counts: dict[str, int]
