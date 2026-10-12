from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from models import TaskModel, TaskStatus
from recurring_models import RecurringTaskModel, RecurringGeneratedModel, RecurringRule
import uuid


def _rule_out(r: RecurringTaskModel) -> RecurringRule:
    return RecurringRule(
        id=r.id, title=r.title, task_type=r.task_type,
        time_start=r.time_start, time_end=r.time_end,
        duration_minutes=r.duration_minutes, routine_id=r.routine_id,
        days=[int(d) for d in r.days.split(",") if d != ""], start_date=r.start_date,
    )


def get_rule(db: Session, rule_id: str) -> RecurringRule | None:
    r = db.query(RecurringTaskModel).filter(RecurringTaskModel.id == rule_id).first()
    return _rule_out(r) if r else None


def get_all_rules(db: Session) -> list[RecurringRule]:
    return [_rule_out(r) for r in db.query(RecurringTaskModel).all()]


def materialize(db: Session, target: date):
    """Создаёт реальные задачи на дату по всем подходящим правилам (идемпотентно)"""
    rules = db.query(RecurringTaskModel).filter(RecurringTaskModel.start_date <= target).all()
    created = False
    for r in rules:
        if str(target.weekday()) not in r.days.split(","):
            continue
        done = db.query(RecurringGeneratedModel).filter(
            RecurringGeneratedModel.recurring_id == r.id,
            RecurringGeneratedModel.date == target,
        ).first()
        if done:
            continue
        order_index = None
        if r.duration_minutes is not None:
            existing = db.query(TaskModel.order_index).filter(TaskModel.date == target).all()
            order_index = max((o[0] for o in existing if o[0] is not None), default=-1) + 1
        db.add(TaskModel(
            id=str(uuid.uuid4()), title=r.title, task_type=r.task_type, status=TaskStatus.todo,
            time_start=r.time_start, time_end=r.time_end,
            duration_minutes=r.duration_minutes, order_index=order_index,
            date=target, routine_id=r.routine_id, recurring_id=r.id,
        ))
        db.add(RecurringGeneratedModel(recurring_id=r.id, date=target))
        created = True
    if created:
        db.commit()


def _drop_upcoming(db: Session, rule_id: str):
    """Убирает ещё не выполненные экземпляры с сегодняшнего дня — они пересоздадутся по новым правилам"""
    today = date.today()
    db.query(TaskModel).filter(
        TaskModel.recurring_id == rule_id, TaskModel.date >= today,
        TaskModel.status == TaskStatus.todo,
    ).delete(synchronize_session=False)
    db.query(RecurringGeneratedModel).filter(
        RecurringGeneratedModel.recurring_id == rule_id,
        RecurringGeneratedModel.date >= today,
    ).delete(synchronize_session=False)


def create_rule(db: Session, data: dict) -> RecurringRule:
    data = dict(data)
    link_task_id = data.pop("link_task_id", None)
    # Правило действует с понедельника той недели, где создано, — чтобы выбранные дни
    # этой недели не терялись, если задачу добавили в середине недели
    data["start_date"] = data["start_date"] - timedelta(days=data["start_date"].weekday())
    data["days"] = ",".join(str(d) for d in data["days"])
    data["task_type"] = data["task_type"].value if hasattr(data["task_type"], "value") else data["task_type"]
    r = RecurringTaskModel(id=str(uuid.uuid4()), **data)
    db.add(r)
    if link_task_id:
        task = db.query(TaskModel).filter(TaskModel.id == link_task_id).first()
        if task:
            task.recurring_id = r.id
            db.add(RecurringGeneratedModel(recurring_id=r.id, date=task.date))
    db.commit()
    return _rule_out(r)


def update_rule(db: Session, rule_id: str, updates: dict) -> RecurringRule | None:
    r = db.query(RecurringTaskModel).filter(RecurringTaskModel.id == rule_id).first()
    if not r:
        return None
    for key, value in updates.items():
        if key == "days":
            value = ",".join(str(d) for d in value)
        elif key == "task_type" and value is not None:
            value = value.value if hasattr(value, "value") else value
        elif value is None and key in ("title", "task_type"):
            continue
        setattr(r, key, value)
    _drop_upcoming(db, rule_id)
    db.commit()
    return _rule_out(r)


def delete_rule(db: Session, rule_id: str) -> bool:
    r = db.query(RecurringTaskModel).filter(RecurringTaskModel.id == rule_id).first()
    if not r:
        return False
    _drop_upcoming(db, rule_id)
    # Прошлые экземпляры остаются обычными задачами
    db.query(TaskModel).filter(TaskModel.recurring_id == rule_id).update(
        {TaskModel.recurring_id: None}, synchronize_session=False)
    db.query(RecurringGeneratedModel).filter(
        RecurringGeneratedModel.recurring_id == rule_id).delete(synchronize_session=False)
    db.delete(r)
    db.commit()
    return True
