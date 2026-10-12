from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import profile_db
from profile_models import PlayerProfile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=PlayerProfile)
def get_profile(db: Session = Depends(get_db)):
    """Получить полный профиль игрока (уровень, XP, характеристики)"""
    return profile_db.get_profile(db)


@router.post("/recalculate", response_model=PlayerProfile)
def recalculate(db: Session = Depends(get_db)):
    """
    Полный пересчёт профиля из истории данных.
    Используется при первом открытии или вручную.
    """
    return profile_db.recalculate_all(db)


@router.post("/reset", response_model=PlayerProfile)
def reset(db: Session = Depends(get_db)):
    """
    Полный сброс профиля: XP, уровни, статы.
    Очищает все тестовые данные.
    """
    return profile_db.reset_profile(db)
