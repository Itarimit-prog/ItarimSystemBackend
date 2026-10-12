from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Float, Boolean
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
    goal_id = Column(String, nullable=True)  # если roadmap принадлежит цели


class RoadmapStepModel(Base):
    """Этап внутри roadmap"""
    __tablename__ = "roadmap_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(String, nullable=False)
    label = Column(String(100), nullable=False)
    position = Column(Integer, default=0)
    x = Column(Float, nullable=True)  # координаты узла на канвасе
    y = Column(Float, nullable=True)
    parent_step_id = Column(String, nullable=True)  # от какого узла идёт связь
    done = Column(Boolean, default=False)
    color = Column(String(20), nullable=True)  # цвет узла на холсте


class RoadmapEdgeModel(Base):
    """Связь (стрелка) между двумя этапами: from_id -> to_id"""
    __tablename__ = "roadmap_edges"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id = Column(String, nullable=False)
    from_id = Column(String, nullable=False)
    to_id = Column(String, nullable=False)


# ── Pydantic схемы для API ──

class RoadmapStep(BaseModel):
    id: str
    label: str
    position: int = 0
    x: float = 0
    y: float = 0
    done: bool = False
    color: Optional[str] = None

    class Config:
        from_attributes = True


class RoadmapEdge(BaseModel):
    id: str
    from_id: str
    to_id: str

    class Config:
        from_attributes = True


class Roadmap(BaseModel):
    id: str
    name: str
    position: int = 0
    current_step_id: Optional[str] = None
    goal_id: Optional[str] = None
    steps: List[RoadmapStep] = []
    edges: List[RoadmapEdge] = []

    class Config:
        from_attributes = True


class RoadmapCreate(BaseModel):
    name: str


class RoadmapUpdate(BaseModel):
    name: Optional[str] = None
    current_step_id: Optional[str] = None


class RoadmapStepCreate(BaseModel):
    label: str
    parent_step_id: Optional[str] = None  # если задан — сразу создаётся связь parent -> новый этап
    x: Optional[float] = None
    y: Optional[float] = None
    color: Optional[str] = None


class RoadmapStepUpdate(BaseModel):
    label: Optional[str] = None
    position: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    done: Optional[bool] = None
    color: Optional[str] = None


class RoadmapEdgeCreate(BaseModel):
    from_id: str
    to_id: str
