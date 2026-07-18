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


class AchievementDefModel(Base):
    """Определения достижений (справочник)"""
    __tablename__ = "achievement_defs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False, unique=True)  # first_workout, iron_will, etc.
    title = Column(String(100), nullable=False)
    description = Column(String(300), nullable=False)
    icon = Column(String(10), default="🏅")
    stat_key = Column(String(30), nullable=True)  # какую характеристику качает
    xp_reward = Column(Integer, default=50)


class UnlockedAchievementModel(Base):
    """Разблокированные достижения игрока"""
    __tablename__ = "unlocked_achievements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    achievement_code = Column(String(50), nullable=False, unique=True)
    unlocked_at = Column(String(30), nullable=False)  # ISO datetime


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


class Achievement(BaseModel):
    code: str
    title: str
    description: str
    icon: str
    stat_key: Optional[str] = None
    xp_reward: int
    unlocked_at: str  # ISO datetime


class AchievementUnlockEvent(BaseModel):
    """Событие разблокировки — для уведомлений"""
    achievement: Achievement
    xp_gained: int
    stat_gained: Optional[str] = None
    stat_xp_gained: int = 0


class XpResult(BaseModel):
    """Результат начисления XP — для ответов API"""
    xp_gained: int
    stat_key: Optional[str] = None
    stat_label: Optional[str] = None
    level: int = 1
    level_up: bool = False
