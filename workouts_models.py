from __future__ import annotations
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Float, Text
from database import Base
from typing import List, Optional
import uuid


# ── SQLAlchemy ORM модели ──

class WorkoutModel(Base):
    """SQLAlchemy ORM модель для тренировок"""
    __tablename__ = "workouts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(String(10), nullable=False)  # ISO format
    duration_minutes = Column(Integer, nullable=False)
    exercises = Column(String, nullable=False)  # JSON array of exercise IDs
    notes = Column(Text, nullable=True)


class ExerciseModel(Base):
    """SQLAlchemy ORM модель для упражнений"""
    __tablename__ = "exercises"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    exercise_type = Column(String(50), nullable=False)  # strength | cardio | flexibility
    muscle_groups = Column(String, nullable=False)  # JSON array
    max_weight = Column(Float, nullable=True)
    max_reps = Column(Integer, nullable=True)


class UserProfileModel(Base):
    """SQLAlchemy ORM модель для профиля пользователя"""
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, default=1)  # Только одна запись
    height_cm = Column(Float, nullable=False, default=180.0)
    weight_kg = Column(Float, nullable=False, default=75.0)


# ── Pydantic схемы для API ──

class WorkoutBase(BaseModel):
    date: str  # ISO format
    duration_minutes: int
    exercises: List[str]  # list of exercise IDs
    notes: Optional[str] = None


class Workout(WorkoutBase):
    id: str

    class Config:
        from_attributes = True


class WorkoutCreate(WorkoutBase):
    pass


class WorkoutUpdate(BaseModel):
    date: Optional[str] = None
    duration_minutes: Optional[int] = None
    exercises: Optional[List[str]] = None
    notes: Optional[str] = None


class ExerciseBase(BaseModel):
    name: str
    description: Optional[str] = None
    exercise_type: str  # strength | cardio | flexibility
    muscle_groups: List[str]
    max_weight: Optional[float] = None
    max_reps: Optional[int] = None


class Exercise(ExerciseBase):
    id: str

    class Config:
        from_attributes = True


class ExerciseCreate(ExerciseBase):
    pass


class UserProfile(BaseModel):
    height_cm: float
    weight_kg: float

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
