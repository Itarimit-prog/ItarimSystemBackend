from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from achievements_models import Achievement, AchievementCreate, AchievementUpdate
from database import get_db
import achievements_db

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("/", response_model=list[Achievement])
def get_achievements(db: Session = Depends(get_db)):
    return achievements_db.get_all(db)


@router.post("/", response_model=Achievement, status_code=201)
def create_achievement(payload: AchievementCreate, db: Session = Depends(get_db)):
    return achievements_db.create(db, payload.model_dump())


@router.patch("/{achievement_id}", response_model=Achievement)
def update_achievement(achievement_id: str, payload: AchievementUpdate, db: Session = Depends(get_db)):
    updated = achievements_db.update(db, achievement_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Достижение не найдено")
    return updated


@router.delete("/{achievement_id}", status_code=204)
def delete_achievement(achievement_id: str, db: Session = Depends(get_db)):
    if not achievements_db.delete(db, achievement_id):
        raise HTTPException(status_code=404, detail="Достижение не найдено")
