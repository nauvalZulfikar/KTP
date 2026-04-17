"""Orchestrates a schedule run: load TaskRows → domain Tasks → scheduler → persist."""

from __future__ import annotations

from sqlmodel import Session, select

from app.core.metrics import late_products, machine_utilization, waiting_time_by
from app.core.models import Task
from app.core.scheduler import schedule
from app.models import ScheduledAssignment, ScheduleRun, TaskRow
from app.schemas.schedule import MetricsRead


def _taskrow_to_domain(row: TaskRow) -> Task:
    return Task(
        unique_id=row.unique_id,
        product_name=row.product_name,
        component=row.component,
        machine=row.machine_number,
        quantity=float(row.quantity_required),
        run_time_per_1000=row.run_time_per_1000,
        order_processing_date=row.order_processing_date,
        promised_delivery_date=row.promised_delivery_date,
    )


def run_and_persist(session: Session, notes: str | None = None) -> ScheduleRun:
    rows = list(session.exec(select(TaskRow)).all())
    if not rows:
        raise ValueError("No tasks to schedule — import data first.")

    task_db_id_by_key: dict[tuple[int, str], int] = {
        (r.unique_id, r.component): r.id
        for r in rows
        if r.id is not None
    }
    scheduled = schedule([_taskrow_to_domain(r) for r in rows])

    run = ScheduleRun(notes=notes)
    session.add(run)
    session.flush()
    assert run.id is not None

    split_counter: dict[tuple[int, str], int] = {}
    for t in scheduled:
        if t.start_time is None or t.end_time is None:
            continue
        key = (t.unique_id, t.component)
        task_id = task_db_id_by_key.get(key)
        if task_id is None:
            continue
        idx = split_counter.get(key, 0)
        split_counter[key] = idx + 1
        session.add(
            ScheduledAssignment(
                run_id=run.id,
                task_id=task_id,
                split_index=idx,
                assigned_quantity=t.quantity,
                start_time=t.start_time,
                end_time=t.end_time,
            )
        )

    session.commit()
    session.refresh(run)
    return run


def compute_metrics(session: Session, run_id: int) -> MetricsRead:
    assignments = list(
        session.exec(
            select(ScheduledAssignment).where(ScheduledAssignment.run_id == run_id)
        ).all()
    )
    if not assignments:
        return MetricsRead(
            machine_utilization={},
            component_waiting_days={},
            product_waiting_days={},
            late_counts={},
        )

    task_by_id = {
        r.id: r for r in session.exec(select(TaskRow)).all() if r.id is not None
    }
    domain_tasks: list[Task] = []
    for a in assignments:
        tr = task_by_id.get(a.task_id)
        if tr is None:
            continue
        domain_tasks.append(
            Task(
                unique_id=tr.unique_id,
                product_name=tr.product_name,
                component=tr.component,
                machine=tr.machine_number,
                quantity=a.assigned_quantity,
                run_time_per_1000=tr.run_time_per_1000,
                order_processing_date=tr.order_processing_date,
                promised_delivery_date=tr.promised_delivery_date,
                start_time=a.start_time,
                end_time=a.end_time,
            )
        )

    return MetricsRead(
        machine_utilization=machine_utilization(domain_tasks),
        component_waiting_days=waiting_time_by(
            domain_tasks,
            group_fn=lambda t: t.component,
            start_fn=lambda t: t.order_processing_date,
            end_fn=lambda t: t.start_time,
        ),
        product_waiting_days=waiting_time_by(
            domain_tasks,
            group_fn=lambda t: t.product_name,
            start_fn=lambda t: t.order_processing_date,
            end_fn=lambda t: t.start_time,
        ),
        late_counts=late_products(domain_tasks),
    )
