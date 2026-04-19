from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import delete, text
from sqlmodel import Session, desc, select

from app.db import get_session
from app.models import ScheduledAssignment, ScheduleRun
from app.schemas.schedule import (
    MetricsRead,
    ScheduledAssignmentRead,
    ScheduleRunCreate,
    ScheduleRunDetail,
    ScheduleRunRead,
)
from app.services.scheduling import compute_metrics, run_and_persist

router = APIRouter(tags=["schedule"])


@router.post(
    "/schedule/run",
    response_model=ScheduleRunRead,
    status_code=status.HTTP_201_CREATED,
)
def trigger_run(
    payload: ScheduleRunCreate = Body(default_factory=ScheduleRunCreate),
    session: Session = Depends(get_session),
) -> ScheduleRun:
    try:
        return run_and_persist(session, notes=payload.notes)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e


@router.get("/runs", response_model=list[ScheduleRunRead])
def list_runs(session: Session = Depends(get_session)) -> list[ScheduleRun]:
    return list(session.exec(select(ScheduleRun).order_by(desc(ScheduleRun.created_at))).all())


@router.get("/runs/{run_id}", response_model=ScheduleRunDetail)
def get_run(run_id: int, session: Session = Depends(get_session)) -> ScheduleRunDetail:
    run = session.get(ScheduleRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    assignments = session.exec(
        select(ScheduledAssignment)
        .where(ScheduledAssignment.run_id == run_id)
        .order_by(ScheduledAssignment.start_time)
    ).all()
    return ScheduleRunDetail(
        id=run.id,  # type: ignore[arg-type]
        created_at=run.created_at,
        notes=run.notes,
        assignments=[ScheduledAssignmentRead.model_validate(a) for a in assignments],
    )


@router.get("/runs/{run_id}/metrics", response_model=MetricsRead)
def get_run_metrics(run_id: int, session: Session = Depends(get_session)) -> MetricsRead:
    if session.get(ScheduleRun, run_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return compute_metrics(session, run_id)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: int, session: Session = Depends(get_session)) -> None:
    run = session.get(ScheduleRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    session.execute(delete(ScheduledAssignment).where(ScheduledAssignment.run_id == run_id))
    session.delete(run)
    session.commit()


@router.delete("/runs", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_runs(session: Session = Depends(get_session)) -> None:
    """Wipe every ScheduleRun + ScheduledAssignment. Task master data is left intact.
    After this, the next run's id is 1 (SQLite reuses rowids when the table is empty)."""
    session.execute(delete(ScheduledAssignment))
    session.execute(delete(ScheduleRun))
    # Reset sqlite_sequence so ids restart at 1 even if AUTOINCREMENT is in use.
    try:
        session.execute(
            text(
                "DELETE FROM sqlite_sequence WHERE name IN ('schedule_run', 'scheduled_assignment')"
            )
        )
    except Exception:
        pass
    session.commit()
