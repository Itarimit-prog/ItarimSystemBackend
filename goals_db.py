from datetime import datetime
from sqlalchemy.orm import Session
from goals_models import GoalModel, Goal
from roadmap_models import RoadmapModel
import roadmap_db
import uuid


def _goal_out(db: Session, g: GoalModel) -> Goal:
    rm = db.query(RoadmapModel).filter(RoadmapModel.goal_id == g.id).first()
    return Goal(
        id=g.id, name=g.name, description=g.description,
        target_count=g.target_count, current_count=g.current_count,
        position=g.position, created_at=g.created_at, completed_at=g.completed_at,
        roadmap_id=rm.id if rm else None,
    )


def get_all_goals(db: Session) -> list[Goal]:
    goals = db.query(GoalModel).order_by(GoalModel.position, GoalModel.created_at).all()
    return [_goal_out(db, g) for g in goals]


def create_goal(db: Session, name: str, description: str | None, target_count: int) -> Goal:
    g = GoalModel(
        id=str(uuid.uuid4()), name=name, description=description,
        target_count=target_count, current_count=0,
        position=db.query(GoalModel).count(),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    db.add(g)
    db.commit()
    # К каждой цели сразу создаётся свой роадмап
    roadmap_db.create_roadmap(db, name, goal_id=g.id)
    db.refresh(g)
    return _goal_out(db, g)


def update_goal(db: Session, goal_id: str, updates: dict) -> Goal | None:
    g = db.query(GoalModel).filter(GoalModel.id == goal_id).first()
    if not g:
        return None
    for key, value in updates.items():
        if value is None and key in ("name", "target_count"):
            continue
        setattr(g, key, value)
    if "name" in updates and updates["name"]:
        rm = db.query(RoadmapModel).filter(RoadmapModel.goal_id == g.id).first()
        if rm:
            rm.name = g.name
    _sync_completion(g)
    db.commit()
    db.refresh(g)
    return _goal_out(db, g)


def add_progress(db: Session, goal_id: str, delta: int) -> Goal | None:
    g = db.query(GoalModel).filter(GoalModel.id == goal_id).first()
    if not g:
        return None
    g.current_count = max(0, min(g.target_count, g.current_count + delta))
    _sync_completion(g)
    db.commit()
    db.refresh(g)
    return _goal_out(db, g)


def _sync_completion(g: GoalModel):
    if g.current_count >= g.target_count:
        g.current_count = g.target_count
        if not g.completed_at:
            g.completed_at = datetime.now().isoformat(timespec="seconds")
    else:
        g.completed_at = None


def delete_goal(db: Session, goal_id: str) -> bool:
    g = db.query(GoalModel).filter(GoalModel.id == goal_id).first()
    if not g:
        return False
    roadmap_db.delete_roadmaps_of_goal(db, goal_id)
    db.delete(g)
    db.commit()
    return True
