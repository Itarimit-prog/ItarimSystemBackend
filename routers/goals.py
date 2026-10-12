from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from goals_models import Goal, GoalCreate, GoalUpdate, GoalProgress
from database import get_db
import goals_db

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/", response_model=list[Goal])
def get_goals(db: Session = Depends(get_db)):
    return goals_db.get_all_goals(db)


@router.post("/", response_model=Goal, status_code=201)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)):
    return goals_db.create_goal(db, payload.name, payload.description, payload.target_count)


@router.patch("/{goal_id}", response_model=Goal)
def update_goal(goal_id: str, payload: GoalUpdate, db: Session = Depends(get_db)):
    updated = goals_db.update_goal(db, goal_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    return updated


@router.post("/{goal_id}/progress", response_model=Goal)
def add_progress(goal_id: str, payload: GoalProgress, db: Session = Depends(get_db)):
    updated = goals_db.add_progress(db, goal_id, payload.delta)
    if not updated:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    return updated


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str, db: Session = Depends(get_db)):
    if not goals_db.delete_goal(db, goal_id):
        raise HTTPException(status_code=404, detail="Цель не найдена")
