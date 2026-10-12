from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import Column, String, Integer, Float
from database import Base
import uuid


# ── SQLAlchemy ORM модели ──

class PlayerModel(Base):
    """Общий профиль игрока — уровень и XP"""
    __tablename__ = "player"

    id = Column(Integer, primary_key=True, default=1)  # одна запись
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)


class StatModel(Base):
    """Характеристики персонажа (6 штук)"""
    __tablename__ = "player_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    stat_key = Column(String(30), nullable=False, unique=True)  # strength, health, etc.
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)


# ── Pydantic схемы для API ──

class Stat(BaseModel):
    stat_key: str
    xp: int
    level: int


class PlayerProfile(BaseModel):
    total_xp: int
    level: int
    xp_to_next: int  # сколько XP нужно до следующего уровня
    stats: List[Stat]


class XpResult(BaseModel):
    """Результат начисления XP — для ответов API"""
    xp_gained: int
    stat_key: Optional[str] = None
    stat_label: Optional[str] = None
    level: int = 1
    level_up: bool = False
