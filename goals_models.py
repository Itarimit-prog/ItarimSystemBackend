from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer
from database import Base
from typing import Optional
import uuid


class GoalModel(Base):
    """Цель со счётчиком: нужно набрать target_count выполнений"""
    __tablename__ = "goals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    target_count = Column(Integer, nullable=False, default=1)
    current_count = Column(Integer, nullable=False, default=0)
    position = Column(Integer, default=0)
    created_at = Column(String(30), nullable=False)
    completed_at = Column(String(30), nullable=True)


class Goal(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    target_count: int
    current_count: int
    position: int = 0
    created_at: str
    completed_at: Optional[str] = None
    roadmap_id: Optional[str] = None

    class Config:
        from_attributes = True


class GoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    target_count: int = Field(..., ge=1, le=100000)


class GoalUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    target_count: Optional[int] = Field(default=None, ge=1, le=100000)


class GoalProgress(BaseModel):
    delta: int = 1
