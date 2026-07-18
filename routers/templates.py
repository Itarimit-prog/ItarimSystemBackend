from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from models import Template, TemplateCreate, ApplyTemplateRequest, Task, TaskStatus
from database import get_db
import db as tasks_db
import uuid

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=list[Template])
def get_templates(session: Session = Depends(get_db)):
    return tasks_db.get_all_templates(session)


@router.post("/", response_model=Template, status_code=201)
def create_template(payload: TemplateCreate, session: Session = Depends(get_db)):
    template = Template(id=str(uuid.uuid4()), **payload.model_dump())
    return tasks_db.create_template(session, template)


@router.post("/apply", response_model=list[Task])
def apply_template(payload: ApplyTemplateRequest, session: Session = Depends(get_db)):
    template = tasks_db.get_template(session, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")

    created_tasks = []
    for item in template.tasks:
        task = Task(
            id=str(uuid.uuid4()),
            title=item.title,
            task_type=item.task_type,
            status=TaskStatus.todo,
            time_start=item.time_start,
            time_end=item.time_end,
            date=payload.target_date,
        )
        tasks_db.create_task(session, task)
        created_tasks.append(task)

    return created_tasks


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: str, session: Session = Depends(get_db)):
    if not tasks_db.delete_template(session, template_id):
        raise HTTPException(status_code=404, detail="Шаблон не найден")
