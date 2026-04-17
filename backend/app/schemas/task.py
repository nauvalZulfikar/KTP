from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    unique_id: int
    sr_no: int | None = None
    product_name: str
    order_processing_date: datetime
    promised_delivery_date: datetime
    quantity_required: int
    component: str
    operation: str | None = None
    process_type: str | None = None
    machine_number: str
    run_time_per_1000: float
    cycle_time_seconds: float | None = None
    setup_time_seconds: float | None = None
    status: str = "InProgress"


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TaskUpdate(BaseModel):
    unique_id: int | None = None
    sr_no: int | None = None
    product_name: str | None = None
    order_processing_date: datetime | None = None
    promised_delivery_date: datetime | None = None
    quantity_required: int | None = None
    component: str | None = None
    operation: str | None = None
    process_type: str | None = None
    machine_number: str | None = None
    run_time_per_1000: float | None = None
    cycle_time_seconds: float | None = None
    setup_time_seconds: float | None = None
    status: str | None = None
