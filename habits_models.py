from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Text, Enum as SQLEnum
from database import Base
from enum import Enum
import uuid


# ── SQLAlchemy ORM модели ──

class HabitKind(str, Enum):
    good = "good"
    bad = "bad"


class FreqType(str, Enum):
    days = "days"       # конкретные дни недели
    times = "times"     # N раз в день


class HabitModel(Base):
    """SQLAlchemy ORM модель для привычек"""
    __tablename__ = "habits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    kind = Column(SQLEnum(HabitKind), nullable=False)
    freq_type = Column(SQLEnum(FreqType), default=FreqType.days)
    freq_days = Column(String, nullable=True)  # JSON array: [0,1,2]
    freq_times = Column(Integer, nullable=True)


class CheckModel(Base):
    """SQLAlchemy ORM модель для отметок выполнения"""
    __tablename__ = "checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    habit_id = Column(String, nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    check_index = Column(Integer, default=0)


class RelapseModel(Base):
    """SQLAlchemy ORM модель для срывов"""
    __tablename__ = "relapses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    habit_id = Column(String, nullable=False)
    timestamp = Column(String(30), nullable=False)  # ISO datetime


# ── Pydantic схемы для API ──

# Переиспользуем ORM Enums для Pydantic
HabitKindPydantic = HabitKind
FreqTypePydantic = FreqType


class HabitBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    kind: HabitKind
    freq_type: FreqType = FreqType.days
    freq_days: Optional[List[int]] = None   # [0..6] пн=0, вс=6
    freq_times: Optional[int] = None        # кол-во раз в день


class HabitCreate(HabitBase):
    pass


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    freq_type: Optional[FreqType] = None
    freq_days: Optional[List[int]] = None
    freq_times: Optional[int] = None


class Habit(HabitBase):
    id: str


# Отметка выполнения хорошей привычки
class CheckBase(BaseModel):
    habit_id: str
    date: str        # YYYY-MM-DD
    check_index: int = 0   # для freq_times: 0, 1, 2...


class CheckCreate(CheckBase):
    pass


class Check(CheckBase):
    id: str


# Срыв плохой привычки
class RelapseBase(BaseModel):
    habit_id: str
    timestamp: str   # ISO datetime


class RelapseCreate(BaseModel):
    habit_id: str


class Relapse(RelapseBase):
    id: str
