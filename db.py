from datetime import date
from sqlalchemy.orm import Session
from models import TaskModel, TaskCreate, TaskUpdate, Task, TemplateModel, TemplateCreate, Template, TemplateTaskItem
import uuid
import json


# Seed data function removed to avoid test data in production
def _placeholder_seed(): pass


def _task_out(t: TaskModel) -> Task:
    return Task(
        id=t.id,
        title=t.title,
        task_type=t.task_type,
        status=t.status,
        time_start=t.time_start,
        time_end=t.time_end,
        duration_minutes=t.duration_minutes,
        order_index=t.order_index,
        date=t.date,
        routine_id=t.routine_id,
        recurring_id=t.recurring_id
    )


def get_tasks_by_date(db: Session, target_date: date) -> list[Task]:
    import recurring_db
    recurring_db.materialize(db, target_date)
    tasks = db.query(TaskModel).filter(TaskModel.date == target_date).all()
    return [_task_out(t) for t in tasks]


def get_task(db: Session, task_id: str) -> Task | None:
    t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not t:
        return None
    return _task_out(t)


def create_task(db: Session, task: Task) -> Task:
    db_task = TaskModel(
        id=task.id,
        title=task.title,
        task_type=task.task_type,
        status=task.status,
        time_start=task.time_start,
        time_end=task.time_end,
        duration_minutes=task.duration_minutes,
        order_index=task.order_index,
        date=task.date,
        routine_id=task.routine_id,
        recurring_id=task.recurring_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return task


def update_task(db: Session, task_id: str, updates: dict) -> Task | None:
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        return None

    for key, value in updates.items():
        setattr(db_task, key, value)

    db.commit()
    db.refresh(db_task)

    return _task_out(db_task)


def delete_task(db: Session, task_id: str) -> bool:
    db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not db_task:
        return False
    
    db.delete(db_task)
    db.commit()
    return True


def get_all_templates(db: Session) -> list[Template]:
    templates = db.query(TemplateModel).all()
    result = []
    for t in templates:
        tasks_data = json.loads(t.tasks)
        task_items = [TemplateTaskItem(**item) for item in tasks_data]
        result.append(Template(id=t.id, name=t.name, tasks=task_items))
    return result


def get_template(db: Session, template_id: str) -> Template | None:
    t = db.query(TemplateModel).filter(TemplateModel.id == template_id).first()
    if not t:
        return None
    
    tasks_data = json.loads(t.tasks)
    task_items = [TemplateTaskItem(**item) for item in tasks_data]
    return Template(id=t.id, name=t.name, tasks=task_items)


def create_template(db: Session, template: Template) -> Template:
    tasks_json = json.dumps([task.model_dump() for task in template.tasks])
    db_template = TemplateModel(
        id=template.id,
        name=template.name,
        tasks=tasks_json
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return template


def delete_template(db: Session, template_id: str) -> bool:
    db_template = db.query(TemplateModel).filter(TemplateModel.id == template_id).first()
    if not db_template:
        return False
    
    db.delete(db_template)
    db.commit()
    return True


def get_dates_with_tasks(db: Session) -> list[str]:
    dates = db.query(TaskModel.date).distinct().all()
    return [d[0].isoformat() for d in dates if d[0]]
