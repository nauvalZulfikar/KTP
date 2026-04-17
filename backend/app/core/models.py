from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Task:
    """A single production task (one row of the legacy 'P' sheet).

    `quantity` is float to tolerate non-integer remainders produced by gap-splitting
    during scheduling; callers should round at the boundary.
    """

    unique_id: int
    product_name: str
    component: str
    machine: str
    quantity: float
    run_time_per_1000: float
    order_processing_date: datetime
    promised_delivery_date: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def run_time_minutes(self) -> float:
        return self.run_time_per_1000 * self.quantity / 1000.0

    def is_outsource(self) -> bool:
        return self.machine == "OutSrc"

    def is_scheduled(self) -> bool:
        return self.start_time is not None and self.end_time is not None
