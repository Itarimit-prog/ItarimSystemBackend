from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from habits_models import Habit, HabitCreate, HabitUpdate, Check, CheckCreate, Relapse, RelapseCreate
from database import get_db
import habits_db
import profile_db
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("/", response_model=list[Habit])
def get_habits(db: Session = Depends(get_db)):
    return habits_db.get_all_habits(db)


@router.post("/", response_model=Habit, status_code=201)
def create_habit(payload: HabitCreate, db: Session = Depends(get_db)):
    habit = Habit(id=str(uuid.uuid4()), **payload.model_dump())
    return habits_db.create_habit(db, habit)


@router.patch("/{habit_id}", response_model=Habit)
def update_habit(habit_id: str, payload: HabitUpdate, db: Session = Depends(get_db)):
    updated = habits_db.update_habit(db, habit_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(404, "Привычка не найдена")
    return updated


@router.delete("/{habit_id}", status_code=204)
def delete_habit(habit_id: str, db: Session = Depends(get_db)):
    if not habits_db.delete_habit(db, habit_id):
        raise HTTPException(404, "Привычка не найдена")


# Checks
@router.get("/{habit_id}/checks")
def get_checks(habit_id: str, date: str, db: Session = Depends(get_db)):
    return habits_db.get_checks_by_date(db, habit_id, date)


@router.post("/{habit_id}/checks", status_code=201)
def add_check(habit_id: str, payload: CheckCreate, db: Session = Depends(get_db)):
    check = Check(id=str(uuid.uuid4()), **payload.model_dump())
    result_check, created = habits_db.add_check(db, check)

    result = result_check.model_dump()
    result["xp_result"] = None

    # Хорошая привычка → +10 XP к здоровью, но только за реально новый чек —
    # повторный POST на уже отмеченный (habit_id, date, check_index) не должен фармить XP.
    # Чек уже сохранён выше — сбой начисления XP не должен превращать успешную
    # отметку привычки в ошибку 500 для пользователя.
    if created:
        try:
            habit = habits_db.get_habit(db, habit_id)
            if habit and habit.kind == "good":
                xp_data = profile_db.award_xp(db, 10, "health")
                result["xp_result"] = xp_data
        except Exception:
            logger.exception("Не удалось начислить XP за чек привычки %s", habit_id)

    return result


@router.delete("/{habit_id}/checks", status_code=204)
def remove_check(habit_id: str, date: str, check_index: int = 0, db: Session = Depends(get_db)):
    habits_db.remove_check(db, habit_id, date, check_index)

    # Хорошая привычка → отнимаем XP (откат)
    try:
        habit = habits_db.get_habit(db, habit_id)
        if habit and habit.kind == "good":
            profile_db.revoke_xp(db, 10, "health")
    except Exception:
        logger.exception("Не удалось откатить XP за чек привычки %s", habit_id)


# Relapses
@router.get("/{habit_id}/relapses", response_model=list[Relapse])
def get_relapses(habit_id: str, db: Session = Depends(get_db)):
    return habits_db.get_relapses(db, habit_id)


@router.post("/{habit_id}/relapses", response_model=Relapse, status_code=201)
def add_relapse(habit_id: str, db: Session = Depends(get_db)):
    relapse = Relapse(
        id=str(uuid.uuid4()),
        habit_id=habit_id,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    )
    return habits_db.add_relapse(db, relapse)


# Статистика
@router.get("/{habit_id}/stats")
def get_stats(habit_id: str, db: Session = Depends(get_db)):
    pct = habits_db.get_completion_percent(db, habit_id)
    last_relapse = habits_db.get_last_relapse(db, habit_id)
    all_relapses = habits_db.get_relapses(db, habit_id)

    # Рекорд — максимальный промежуток между срывами
    record_seconds = 0
    if all_relapses:
        timestamps = [datetime.fromisoformat(r.timestamp) for r in all_relapses]
        timestamps.sort()
        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i-1]).total_seconds()
            record_seconds = max(record_seconds, diff)
        # Текущий промежуток
        current = (datetime.now(timezone.utc).replace(tzinfo=None) - timestamps[-1]).total_seconds()
        record_seconds = max(record_seconds, current)
    
    # Округляем до целых секунд
    record_seconds = int(record_seconds)

    return {
        "completion_percent": pct,
        "last_relapse": last_relapse.timestamp if last_relapse else None,
        "record_seconds": record_seconds,
    }
