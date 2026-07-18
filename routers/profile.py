from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import profile_db
from profile_models import PlayerProfile, Achievement, AchievementUnlockEvent

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=PlayerProfile)
def get_profile(db: Session = Depends(get_db)):
    """Получить полный профиль игрока (уровень, XP, характеристики)"""
    return profile_db.get_profile(db)


@router.get("/achievements", response_model=list[Achievement])
def get_achievements(db: Session = Depends(get_db)):
    """Получить список разблокированных достижений"""
    return profile_db.get_unlocked_achievements(db)


@router.post("/check-achievements", response_model=list[AchievementUnlockEvent])
def check_achievements(db: Session = Depends(get_db)):
    """
    Проверить и разблокировать новые достижения.
    Возвращает список только что разблокированных.
    """
    return profile_db.check_and_unlock_achievements(db)


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
    Полный сброс профиля: XP, уровни, статы, достижения.
    Очищает все тестовые данные.
    """
    return profile_db.reset_profile(db)
