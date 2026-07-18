from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer
from database import Base
import uuid


# ── SQLAlchemy ORM модели ──

class BoardModel(Base):
    """SQLAlchemy ORM модель для досок"""
    __tablename__ = "boards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)


class KanbanColumnModel(Base):
    """SQLAlchemy ORM модель для колонок"""
    __tablename__ = "columns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String, nullable=False)
    title = Column(String(100), nullable=False)
    color = Column(String(7), default="#1A7AE8")
    position = Column(Integer, default=0)
    is_completed_column = Column(Integer, default=0) # 0 - нет, 1 - да (для совместимости с SQLite/Postgres)


class KanbanCardModel(Base):
    """SQLAlchemy ORM модель для карточек"""
    __tablename__ = "cards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    column_id = Column(String, nullable=False)
    title = Column(String(200), nullable=False)
    deadline = Column(String(10), nullable=True)  # YYYY-MM-DD
    position = Column(Integer, default=0)
    task_id = Column(String, nullable=True)
    completed = Column(Integer, default=0)  # 0 - нет, 1 - да
    completed_at = Column(String(50), nullable=True)  # ISO datetime или YYYY-MM-DD HH:MM


# ── Pydantic схемы для API ──

class BoardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class BoardCreate(BoardBase):
    pass


class Board(BoardBase):
    id: str


class ColumnBase(BaseModel):
    board_id: str
    title: str = Field(..., min_length=1, max_length=100)
    color: str = "#1A7AE8"
    position: int = 0
    is_completed_column: bool = False


class ColumnCreate(ColumnBase):
    pass


class ColumnUpdate(BaseModel):
    title: Optional[str] = None
    color: Optional[str] = None
    position: Optional[int] = None
    is_completed_column: Optional[bool] = None


class KanbanColumn(ColumnBase):
    id: str
    is_completed_column: bool = False


class CardBase(BaseModel):
    column_id: str
    title: str = Field(..., min_length=1, max_length=200)
    deadline: Optional[str] = None
    position: int = 0
    task_id: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    column_id: Optional[str] = None
    title: Optional[str] = None
    deadline: Optional[str] = None
    position: Optional[int] = None
    completed: Optional[bool] = None
    completed_at: Optional[str] = None


class KanbanCard(CardBase):
    id: str
    task_id: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None


class MoveCardRequest(BaseModel):
    card_id: str
    target_column_id: str
    position: int
