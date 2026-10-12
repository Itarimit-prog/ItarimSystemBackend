from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Text, Boolean
from database import Base
from typing import Optional
import uuid


class AchievementModel(Base):
    """Достижение, которое пользователь создаёт сам: название, описание и награда"""
    __tablename__ = "achievements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    reward_name = Column(String(100), nullable=True)
    reward_photo = Column(Text, nullable=True)  # data URL (картинка уменьшается на клиенте)
    done = Column(Boolean, default=False)
    done_at = Column(String(30), nullable=True)
    position = Column(Integer, default=0)
    created_at = Column(String(30), nullable=False)


class MetaModel(Base):
    """Служебные флаги (например, что разовый импорт уже выполнен)"""
    __tablename__ = "app_meta"

    key = Column(String(50), primary_key=True)
    value = Column(String(200), nullable=True)


class Achievement(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    reward_name: Optional[str] = None
    reward_photo: Optional[str] = None
    done: bool = False
    done_at: Optional[str] = None
    position: int = 0
    created_at: str

    class Config:
        from_attributes = True


class AchievementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    reward_name: Optional[str] = Field(default=None, max_length=100)
    reward_photo: Optional[str] = Field(default=None, max_length=3_000_000)


class AchievementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    reward_name: Optional[str] = Field(default=None, max_length=100)
    reward_photo: Optional[str] = Field(default=None, max_length=3_000_000)
    done: Optional[bool] = None
