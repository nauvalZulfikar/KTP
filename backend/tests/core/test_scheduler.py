from datetime import datetime

from app.core.models import Task
from app.core.scheduler import find_gaps, schedule


def _task(
    uid: int,
    product: str,
    component: str,
    machine: str,
    qty: float,
    run_per_1000: float,
    order: datetime,
    promised: datetime,
) -> Task:
    return Task(
        unique_id=uid,
        product_name=product,
        component=component,
        machine=machine,
        quantity=qty,
        run_time_per_1000=run_per_1000,
        order_processing_date=order,
        promised_delivery_date=promised,
    )


def test_empty_input_returns_empty() -> None:
    assert schedule([]) == []


def test_single_task_starts_at_order_date_work_start() -> None:
    order = datetime(2024, 1, 8, 0, 0)  # Monday, midnight
    promised = datetime(2024, 1, 15)
    t = _task(1, "P1", "C1", "M1", qty=1000, run_per_1000=60, order=order, promised=promised)
    result = schedule([t])
    assert len(result) == 1
    scheduled = result[0]
    assert scheduled.start_time == datetime(2024, 1, 8, 9, 0)
    assert scheduled.end_time == datetime(2024, 1, 8, 10, 0)


def test_two_components_same_product_serial() -> None:
    order = datetime(2024, 1, 8)
    promised = datetime(2024, 1, 15)
    c1 = _task(1, "P1", "C1", "M1", qty=1000, run_per_1000=60, order=order, promised=promised)
    c2 = _task(2, "P1", "C2", "M2", qty=1000, run_per_1000=30, order=order, promised=promised)
    result = schedule([c1, c2])
    by_comp = {t.component: t for t in result}
    # C2 must not start before C1 ends
    assert by_comp["C2"].start_time >= by_comp["C1"].end_time


def test_outsource_c1_starts_at_order_date() -> None:
    order = datetime(2024, 1, 8, 14, 30)  # mid-afternoon
    promised = datetime(2024, 1, 20)
    t = _task(1, "P1", "C1", "OutSrc", qty=1000, run_per_1000=60, order=order, promised=promised)
    result = schedule([t])
    # Outsource C1 forces start at 9 AM on the order date regardless of the clock time
    assert result[0].start_time == datetime(2024, 1, 8, 9, 0)


def test_promised_date_priority() -> None:
    order = datetime(2024, 1, 8)
    urgent = _task(1, "A", "C1", "M1", qty=1000, run_per_1000=60,
                   order=order, promised=datetime(2024, 1, 10))
    relaxed = _task(2, "B", "C1", "M1", qty=1000, run_per_1000=60,
                    order=order, promised=datetime(2024, 2, 1))
    # Feed in reverse order; scheduler should still do urgent first
    result = schedule([relaxed, urgent])
    by_id = {t.unique_id: t for t in result}
    assert by_id[1].start_time < by_id[2].start_time


def test_find_gaps_detects_interval() -> None:
    schedule_state = {
        "M1": [
            (datetime(2024, 1, 8, 9, 0), datetime(2024, 1, 8, 10, 0), 0),
            (datetime(2024, 1, 8, 12, 0), datetime(2024, 1, 8, 13, 0), 1),
        ]
    }
    gaps = find_gaps(schedule_state)
    assert gaps["M1"] == [(datetime(2024, 1, 8, 10, 0), datetime(2024, 1, 8, 12, 0))]


def test_input_not_mutated() -> None:
    order = datetime(2024, 1, 8)
    promised = datetime(2024, 1, 15)
    t = _task(1, "P1", "C1", "M1", qty=1000, run_per_1000=60, order=order, promised=promised)
    original_start = t.start_time
    _ = schedule([t])
    assert t.start_time == original_start  # still None
