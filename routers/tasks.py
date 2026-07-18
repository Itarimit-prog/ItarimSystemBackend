from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date
from models import Task, TaskCreate, TaskUpdate
from database import get_db
import db as tasks_db
import profile_db
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Маппинг: task_type → stat_key для XP
_TASK_STAT_MAP = {
    "work": "intelligence",
    "study": "intelligence",
    "rest": "health",
    "routine": "discipline",
    "personal": "charisma",
}


@router.get("/", response_model=list[Task])
def get_tasks(date: date, session: Session = Depends(get_db)):
    return tasks_db.get_tasks_by_date(session, date)


@router.get("/dates")
def get_dates_with_tasks(session: Session = Depends(get_db)):
    return tasks_db.get_dates_with_tasks(session)


@router.post("/", response_model=Task, status_code=201)
def create_task(payload: TaskCreate, session: Session = Depends(get_db)):
    task = Task(id=str(uuid.uuid4()), **payload.model_dump())
    return tasks_db.create_task(session, task)


@router.patch("/{task_id}")
def update_task(task_id: str, payload: TaskUpdate, session: Session = Depends(get_db)):
    # Получаем текущую задачу ДО обновления
    old_task = tasks_db.get_task(session, task_id)

    updated = tasks_db.update_task(session, task_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    result = updated.model_dump()
    result["xp_result"] = None

    # XP начисляется только когда статус меняется на "done"
    if (payload.status == "done"
            and old_task
            and old_task.status != "done"):
        stat_key = _TASK_STAT_MAP.get(updated.task_type)
        xp_data = profile_db.award_xp(session, 15, stat_key)
        result["xp_result"] = xp_data

    return result


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, session: Session = Depends(get_db)):
    if not tasks_db.delete_task(session, task_id):
        raise HTTPException(status_code=404, detail="Задача не найдена")
