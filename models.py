from enum import Enum
from datetime import date, time
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Date, Enum as SQLEnum
from database import Base
import uuid


# ── SQLAlchemy ORM модели ──

class TaskType(str, Enum):
    work = "work"
    study = "study"
    personal = "personal"
    routine = "routine"
    rest = "rest"


class TaskStatus(str, Enum):
    todo = "todo"
    done = "done"
    pending = "pending"


class TaskModel(Base):
    """SQLAlchemy ORM модель для задач"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    task_type = Column(SQLEnum(TaskType), nullable=False)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.todo)
    time_start = Column(String(5), nullable=False)  # "HH:MM"
    time_end = Column(String(5), nullable=False)    # "HH:MM"
    date = Column(Date, nullable=False)


# ── Pydantic схемы для API ──

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    task_type: TaskType
    status: TaskStatus = TaskStatus.todo
    time_start: str  # "HH:MM"
    time_end: str    # "HH:MM"
    date: date


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    task_type: Optional[TaskType] = None
    status: Optional[TaskStatus] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None


class Task(TaskBase):
    id: str

    class Config:
        from_attributes = True


class TemplateTaskItem(BaseModel):
    title: str
    task_type: TaskType
    time_start: str
    time_end: str


class TemplateModel(Base):
    """SQLAlchemy ORM модель для шаблонов"""
    __tablename__ = "templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    # Храним задачи как JSON строку
    tasks = Column(String, nullable=False)  # JSON string


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    tasks: list[TemplateTaskItem]


class TemplateCreate(TemplateBase):
    pass


class Template(TemplateBase):
    id: str

    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    template_id: str
    target_date: date
