from datetime import datetime

from sqlmodel import Field, SQLModel


class TaskRow(SQLModel, table=True):
    """Master row describing one operation on one component of one product.

    Mirrors the legacy 'P' sheet columns. `unique_id` is the original Excel key and
    may repeat across rows if the importer ever ingests multiple workbooks; the `id`
    column is the real DB primary key.
    """

    __tablename__ = "task"

    id: int | None = Field(default=None, primary_key=True)
    unique_id: int = Field(index=True)
    sr_no: int | None = None
    product_name: str = Field(index=True)
    order_processing_date: datetime
    promised_delivery_date: datetime
    quantity_required: int
    component: str = Field(index=True)
    operation: str | None = None
    process_type: str | None = None
    machine_number: str = Field(index=True)
    run_time_per_1000: float
    cycle_time_seconds: float | None = None
    setup_time_seconds: float | None = None
    status: str = Field(default="InProgress")
