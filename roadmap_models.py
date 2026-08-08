from pydantic import BaseModel
from sqlalchemy import Column, String, Integer
from database import Base
from typing import List, Optional
import uuid


# ── SQLAlchemy ORM модели ──

class RoadmapModel(Base):
    """Roadmap — прогресс по цели с этапами (несколько штук, переключаемые)"""
    __tablename__ = "roadmaps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    position = Column(Integer, default=0)
    current_step_id = Column(String, nullable=True)


class RoadmapStepModel(Base):
    """Этап внутри roadmap"""
    __tablename__ = "roadmap_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(String, nullable=False)
    label = Column(String(100), nullable=False)
    position = Column(Integer, default=0)


# ── Pydantic схемы для API ──

class RoadmapStep(BaseModel):
    id: str
    label: str
    position: int = 0

    class Config:
        from_attributes = True


class Roadmap(BaseModel):
    id: str
    name: str
    position: int = 0
    current_step_id: Optional[str] = None
    steps: List[RoadmapStep] = []

    class Config:
        from_attributes = True


class RoadmapCreate(BaseModel):
    name: str


class RoadmapUpdate(BaseModel):
    name: Optional[str] = None
    current_step_id: Optional[str] = None


class RoadmapStepCreate(BaseModel):
    label: str


class RoadmapStepUpdate(BaseModel):
    label: Optional[str] = None
    position: Optional[int] = None
