from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date
from models import Task, TaskCreate, TaskUpdate
from database import get_db
import db as tasks_db
import profile_db
import uuid
import logging

logger = logging.getLogger(__name__)

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

    stat_key = _TASK_STAT_MAP.get(updated.task_type)
    was_done = bool(old_task and old_task.status == "done")
    is_done = updated.status == "done"

    # Задача уже сохранена выше — сбой начисления XP не должен превращать
    # успешное обновление задачи в ошибку 500 для пользователя
    try:
        if is_done and not was_done:
            # Статус стал "done" — начисляем XP
            result["xp_result"] = profile_db.award_xp(session, 15, stat_key)
        elif was_done and not is_done:
            # Статус ушёл с "done" — откатываем ранее начисленный XP,
            # иначе toggle done→todo→done бесконечно фармит очки
            profile_db.revoke_xp(session, 15, stat_key)
    except Exception:
        logger.exception("Не удалось начислить/откатить XP для задачи %s", task_id)

    return result


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, session: Session = Depends(get_db)):
    if not tasks_db.delete_task(session, task_id):
        raise HTTPException(status_code=404, detail="Задача не найдена")
