from datetime import date as date_type
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, String, Integer, Date
from database import Base
from models import TaskType
from typing import Optional
import uuid


class RecurringTaskModel(Base):
    """Правило повторяющейся задачи: в выбранные дни недели задача создаётся сама"""
    __tablename__ = "recurring_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    task_type = Column(String(20), nullable=False)
    time_start = Column(String(5), nullable=True)
    time_end = Column(String(5), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    routine_id = Column(String, nullable=True)
    days = Column(String(20), nullable=False)  # "0,2,4" — дни недели, 0 = понедельник
    start_date = Column(Date, nullable=False)


class RecurringGeneratedModel(Base):
    """Для каких дат задача уже создавалась — чтобы удалённый вручную день не воскресал"""
    __tablename__ = "recurring_generated"

    recurring_id = Column(String, primary_key=True)
    date = Column(Date, primary_key=True)


class RecurringBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    task_type: TaskType
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    duration_minutes: Optional[int] = None
    routine_id: Optional[str] = None
    days: list[int] = Field(..., min_length=1)
    start_date: date_type

    @field_validator("days")
    @classmethod
    def _valid_days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("День недели должен быть от 0 (пн) до 6 (вс)")
        return sorted(set(v))


class RecurringCreate(RecurringBase):
    # Если правило создаётся из уже существующей задачи — она становится первым экземпляром
    link_task_id: Optional[str] = None


class RecurringUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    task_type: Optional[TaskType] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    duration_minutes: Optional[int] = None
    routine_id: Optional[str] = None
    days: Optional[list[int]] = Field(default=None, min_length=1)

    @field_validator("days")
    @classmethod
    def _valid_days(cls, v):
        if v is not None and any(d < 0 or d > 6 for d in v):
            raise ValueError("День недели должен быть от 0 (пн) до 6 (вс)")
        return sorted(set(v)) if v is not None else v


class RecurringRule(RecurringBase):
    id: str
