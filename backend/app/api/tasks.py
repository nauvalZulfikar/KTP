from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import TaskRow
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from scripts.import_excel import load_dataframe, row_to_taskrow

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(session: Session = Depends(get_session)) -> list[TaskRow]:
    return list(session.exec(select(TaskRow).order_by(TaskRow.unique_id, TaskRow.component)).all())


@router.get("/original", response_model=list[TaskRead])
def list_original_tasks() -> list[TaskRead]:
    """Read the source Excel workbook fresh and return task rows as-originally-defined.
    Independent of any Randomise / Modify / Products edits that have hit the DB."""
    df = load_dataframe(settings.excel_path, "As-Is")
    out: list[TaskRead] = []
    for _, row in df.iterrows():
        tr = row_to_taskrow(row)
        out.append(TaskRead(id=tr.unique_id, **tr.model_dump(exclude={"id"})))
    return out


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, session: Session = Depends(get_session)) -> TaskRow:
    task = session.get(TaskRow, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, session: Session = Depends(get_session)) -> TaskRow:
    row = TaskRow(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int, payload: TaskUpdate, session: Session = Depends(get_session)
) -> TaskRow:
    task = session.get(TaskRow, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, session: Session = Depends(get_session)) -> None:
    task = session.get(TaskRow, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    session.delete(task)
    session.commit()
