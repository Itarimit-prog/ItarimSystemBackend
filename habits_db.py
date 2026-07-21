from sqlalchemy.orm import Session
from habits_models import (
    HabitModel, Habit, HabitCreate, HabitUpdate,
    CheckModel, Check, CheckCreate,
    RelapseModel, Relapse, RelapseCreate
)
from datetime import datetime, date, timedelta
import uuid
import json


# Seed data function removed to avoid test data in production
def _placeholder_seed_habits(): pass


# Habits CRUD
def get_all_habits(db: Session) -> list[Habit]:
    habits = db.query(HabitModel).all()
    result = []
    for h in habits:
        freq_days = json.loads(h.freq_days) if h.freq_days else None
        result.append(Habit(
            id=h.id,
            name=h.name,
            description=h.description,
            kind=h.kind,
            freq_type=h.freq_type,
            freq_days=freq_days,
            freq_times=h.freq_times
        ))
    return result

def get_habit(db: Session, habit_id: str) -> Habit | None:
    h = db.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not h:
        return None
    
    freq_days = json.loads(h.freq_days) if h.freq_days else None
    return Habit(
        id=h.id,
        name=h.name,
        description=h.description,
        kind=h.kind,
        freq_type=h.freq_type,
        freq_days=freq_days,
        freq_times=h.freq_times
    )

def create_habit(db: Session, habit: Habit) -> Habit:
    db_habit = HabitModel(
        id=habit.id,
        name=habit.name,
        description=habit.description,
        kind=habit.kind,
        freq_type=habit.freq_type,
        freq_days=json.dumps(habit.freq_days) if habit.freq_days else None,
        freq_times=habit.freq_times
    )
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)
    return habit

def update_habit(db: Session, habit_id: str, updates: dict) -> Habit | None:
    db_habit = db.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not db_habit:
        return None
    
    for key, value in updates.items():
        if key == 'freq_days' and value is not None:
            value = json.dumps(value)
        setattr(db_habit, key, value)
    
    db.commit()
    db.refresh(db_habit)
    
    freq_days = json.loads(db_habit.freq_days) if db_habit.freq_days else None
    return Habit(
        id=db_habit.id,
        name=db_habit.name,
        description=db_habit.description,
        kind=db_habit.kind,
        freq_type=db_habit.freq_type,
        freq_days=freq_days,
        freq_times=db_habit.freq_times
    )

def delete_habit(db: Session, habit_id: str) -> bool:
    db_habit = db.query(HabitModel).filter(HabitModel.id == habit_id).first()
    if not db_habit:
        return False
    
    # Чистим чеки и срывы
    db.query(CheckModel).filter(CheckModel.habit_id == habit_id).delete()
    db.query(RelapseModel).filter(RelapseModel.habit_id == habit_id).delete()
    db.delete(db_habit)
    db.commit()
    return True


# Checks
def get_checks(db: Session, habit_id: str, date_from: str, date_to: str) -> list[Check]:
    checks = db.query(CheckModel).filter(
        CheckModel.habit_id == habit_id,
        CheckModel.date >= date_from,
        CheckModel.date <= date_to
    ).all()
    
    return [Check(id=c.id, habit_id=c.habit_id, date=c.date, check_index=c.check_index) for c in checks]

def get_checks_by_date(db: Session, habit_id: str, date: str) -> list[Check]:
    checks = db.query(CheckModel).filter(
        CheckModel.habit_id == habit_id,
        CheckModel.date == date
    ).all()
    
    return [Check(id=c.id, habit_id=c.habit_id, date=c.date, check_index=c.check_index) for c in checks]

def add_check(db: Session, check: Check) -> tuple[Check, bool]:
    """Возвращает (check, created) — created=False если такой чек уже существовал (без дублей и повторного XP)."""
    existing = db.query(CheckModel).filter(
        CheckModel.habit_id == check.habit_id,
        CheckModel.date == check.date,
        CheckModel.check_index == check.check_index
    ).first()
    if existing:
        return Check(id=existing.id, habit_id=existing.habit_id, date=existing.date, check_index=existing.check_index), False

    db_check = CheckModel(
        id=check.id,
        habit_id=check.habit_id,
        date=check.date,
        check_index=check.check_index
    )
    db.add(db_check)
    db.commit()
    db.refresh(db_check)
    return check, True

def remove_check(db: Session, habit_id: str, date: str, check_index: int) -> bool:
    db_check = db.query(CheckModel).filter(
        CheckModel.habit_id == habit_id,
        CheckModel.date == date,
        CheckModel.check_index == check_index
    ).first()
    
    if not db_check:
        return False
    
    db.delete(db_check)
    db.commit()
    return True


# Relapses
def get_relapses(db: Session, habit_id: str) -> list[Relapse]:
    relapses = db.query(RelapseModel).filter(
        RelapseModel.habit_id == habit_id
    ).order_by(RelapseModel.timestamp).all()
    
    return [Relapse(id=r.id, habit_id=r.habit_id, timestamp=r.timestamp) for r in relapses]

def get_last_relapse(db: Session, habit_id: str) -> Relapse | None:
    r = db.query(RelapseModel).filter(
        RelapseModel.habit_id == habit_id
    ).order_by(RelapseModel.timestamp.desc()).first()
    
    if not r:
        return None
    return Relapse(id=r.id, habit_id=r.habit_id, timestamp=r.timestamp)

def add_relapse(db: Session, relapse: Relapse) -> Relapse:
    db_relapse = RelapseModel(
        id=relapse.id,
        habit_id=relapse.habit_id,
        timestamp=relapse.timestamp
    )
    db.add(db_relapse)
    db.commit()
    db.refresh(db_relapse)
    return relapse


# Статистика: % выполнения за последние 30 дней
def get_completion_percent(db: Session, habit_id: str) -> float:
    habit = get_habit(db, habit_id)
    if not habit or habit.kind != "good":
        return 0.0
    
    today = date.today()
    date_from = (today - timedelta(days=29)).isoformat()
    date_to = today.isoformat()

    total = 0
    done = 0
    
    # Получаем все чеки за период
    all_checks = get_checks(db, habit_id, date_from, date_to)
    
    for i in range(30):
        d = today - timedelta(days=i)
        d_str = d.isoformat()
        weekday = d.weekday()  # 0=пн

        if habit.freq_type == "days":
            freq_days = habit.freq_days or []
            # Убедимся что freq_days - это список чисел
            if isinstance(freq_days, list) and len(freq_days) > 0:
                if weekday in freq_days:
                    total += 1
                    if any(c.date == d_str for c in all_checks):
                        done += 1
        elif habit.freq_type == "times":
            times = habit.freq_times or 1
            total += times
            day_checks = [c for c in all_checks if c.date == d_str]
            done += min(len(day_checks), times)

    return round(done / total * 100, 1) if total > 0 else 0.0
