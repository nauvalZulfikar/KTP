from datetime import datetime

from sqlmodel import Session, select

from app.models import ScheduledAssignment, ScheduleRun, TaskRow


def test_task_row_roundtrip(session: Session) -> None:
    row = TaskRow(
        unique_id=1,
        product_name="Product 1",
        component="C1",
        machine_number="M1",
        quantity_required=9000,
        run_time_per_1000=10.0,
        order_processing_date=datetime(2024, 8, 21),
        promised_delivery_date=datetime(2024, 8, 28),
    )
    session.add(row)
    session.commit()

    loaded = session.exec(select(TaskRow).where(TaskRow.unique_id == 1)).one()
    assert loaded.product_name == "Product 1"
    assert loaded.quantity_required == 9000
    assert loaded.status == "InProgress"


def test_scheduled_assignment_links_task_and_run(session: Session) -> None:
    task = TaskRow(
        unique_id=1,
        product_name="P1",
        component="C1",
        machine_number="M1",
        quantity_required=1000,
        run_time_per_1000=60.0,
        order_processing_date=datetime(2024, 1, 8),
        promised_delivery_date=datetime(2024, 1, 15),
    )
    run = ScheduleRun(notes="initial")
    session.add_all([task, run])
    session.commit()

    assignment = ScheduledAssignment(
        run_id=run.id,
        task_id=task.id,
        assigned_quantity=1000.0,
        start_time=datetime(2024, 1, 8, 9, 0),
        end_time=datetime(2024, 1, 8, 10, 0),
    )
    session.add(assignment)
    session.commit()

    fetched = session.exec(select(ScheduledAssignment)).one()
    assert fetched.task_id == task.id
    assert fetched.run_id == run.id
    assert fetched.split_index == 0


def test_split_assignments_share_task(session: Session) -> None:
    task = TaskRow(
        unique_id=24,
        product_name="Product 7",
        component="C1",
        machine_number="M2",
        quantity_required=8000,
        run_time_per_1000=90.0,
        order_processing_date=datetime(2024, 8, 21),
        promised_delivery_date=datetime(2024, 9, 3),
    )
    run = ScheduleRun()
    session.add_all([task, run])
    session.commit()

    pieces = [
        ScheduledAssignment(
            run_id=run.id, task_id=task.id, split_index=i,
            assigned_quantity=qty,
            start_time=datetime(2024, 8, 21, 9 + i, 0),
            end_time=datetime(2024, 8, 21, 10 + i, 0),
        )
        for i, qty in enumerate([1333.0, 1000.0, 5667.0])
    ]
    session.add_all(pieces)
    session.commit()

    loaded = session.exec(
        select(ScheduledAssignment).where(ScheduledAssignment.task_id == task.id)
    ).all()
    assert len(loaded) == 3
    assert sorted(a.split_index for a in loaded) == [0, 1, 2]
    assert sum(a.assigned_quantity for a in loaded) == 8000.0
