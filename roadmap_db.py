from sqlalchemy.orm import Session
from roadmap_models import (
    RoadmapModel, RoadmapStepModel, RoadmapEdgeModel, Roadmap, RoadmapStep, RoadmapEdge,
)
import uuid

# Шаг сетки при автоматической раскладке узлов на канвасе
GRID_DX = 240
GRID_DY = 130


def _step_out(s: RoadmapStepModel) -> RoadmapStep:
    return RoadmapStep(
        id=s.id, label=s.label, position=s.position,
        x=s.x or 0, y=s.y or 0,
        done=bool(s.done), color=s.color,
    )


def _roadmap_out(db: Session, r: RoadmapModel) -> Roadmap:
    steps = db.query(RoadmapStepModel).filter(
        RoadmapStepModel.roadmap_id == r.id
    ).order_by(RoadmapStepModel.position).all()
    return Roadmap(
        id=r.id,
        name=r.name,
        position=r.position,
        current_step_id=r.current_step_id,
        goal_id=r.goal_id,
        steps=[_step_out(s) for s in steps],
        edges=[
            RoadmapEdge(id=e.id, from_id=e.from_id, to_id=e.to_id)
            for e in db.query(RoadmapEdgeModel).filter(RoadmapEdgeModel.roadmap_id == r.id).all()
        ],
    )


def ensure_step_layout(db: Session):
    """Разовая миграция: старым (линейным) этапам задаём координаты и связи в цепочку"""
    legacy = db.query(RoadmapStepModel).filter(RoadmapStepModel.x.is_(None)).all()
    if not legacy:
        return
    roadmap_ids = {s.roadmap_id for s in legacy}
    for rid in roadmap_ids:
        steps = db.query(RoadmapStepModel).filter(
            RoadmapStepModel.roadmap_id == rid
        ).order_by(RoadmapStepModel.position).all()
        current = db.query(RoadmapModel.current_step_id).filter(RoadmapModel.id == rid).scalar()
        # Раньше "пройденными" считались все этапы до текущего — переносим это в флаг done
        current_idx = next((i for i, st in enumerate(steps) if st.id == current), -1)
        prev = None
        for i, s in enumerate(steps):
            if s.x is None:
                s.done = i < current_idx
                s.x = 0
                s.y = i * GRID_DY
                s.parent_step_id = prev.id if prev else None
            prev = s
    db.commit()


def migrate_parents_to_edges(db: Session):
    """Разовая миграция: «родитель» узла (дерево) -> полноценная связь-стрелка.
    После переноса parent_step_id обнуляем, чтобы удалённые пользователем связи не воскресали."""
    steps = db.query(RoadmapStepModel).filter(RoadmapStepModel.parent_step_id.isnot(None)).all()
    if not steps:
        return
    for st in steps:
        exists = db.query(RoadmapEdgeModel).filter(
            RoadmapEdgeModel.from_id == st.parent_step_id, RoadmapEdgeModel.to_id == st.id
        ).first()
        if not exists:
            db.add(RoadmapEdgeModel(
                id=str(uuid.uuid4()), roadmap_id=st.roadmap_id,
                from_id=st.parent_step_id, to_id=st.id,
            ))
        st.parent_step_id = None
    db.commit()


def get_all_roadmaps(db: Session) -> list[Roadmap]:
    roadmaps = db.query(RoadmapModel).order_by(RoadmapModel.position).all()
    return [_roadmap_out(db, r) for r in roadmaps]


def get_roadmap(db: Session, roadmap_id: str) -> Roadmap | None:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    return _roadmap_out(db, r) if r else None


def create_roadmap(db: Session, name: str, goal_id: str | None = None) -> Roadmap:
    position = db.query(RoadmapModel).count()
    r = RoadmapModel(id=str(uuid.uuid4()), name=name, position=position, goal_id=goal_id)
    db.add(r)
    db.commit()
    db.refresh(r)
    return _roadmap_out(db, r)


def update_roadmap(db: Session, roadmap_id: str, updates: dict) -> Roadmap | None:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if not r:
        return None
    for key, value in updates.items():
        setattr(r, key, value)
    db.commit()
    db.refresh(r)
    return _roadmap_out(db, r)


def delete_roadmap(db: Session, roadmap_id: str) -> bool:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if not r:
        return False
    db.query(RoadmapStepModel).filter(RoadmapStepModel.roadmap_id == roadmap_id).delete()
    db.query(RoadmapEdgeModel).filter(RoadmapEdgeModel.roadmap_id == roadmap_id).delete()
    db.delete(r)
    db.commit()
    return True


def delete_roadmaps_of_goal(db: Session, goal_id: str):
    for r in db.query(RoadmapModel).filter(RoadmapModel.goal_id == goal_id).all():
        db.query(RoadmapStepModel).filter(RoadmapStepModel.roadmap_id == r.id).delete()
        db.query(RoadmapEdgeModel).filter(RoadmapEdgeModel.roadmap_id == r.id).delete()
        db.delete(r)
    db.commit()


def add_step(
    db: Session, roadmap_id: str, label: str,
    parent_step_id: str | None = None, x: float | None = None, y: float | None = None,
    color: str | None = None,
) -> Roadmap | None:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if not r:
        return None
    steps = db.query(RoadmapStepModel).filter(RoadmapStepModel.roadmap_id == roadmap_id).all()
    parent = next((s for s in steps if s.id == parent_step_id), None) if parent_step_id else None

    if x is None or y is None:
        if parent:
            siblings = db.query(RoadmapEdgeModel).filter(RoadmapEdgeModel.from_id == parent.id).count()
            x = (parent.x or 0) + siblings * GRID_DX
            y = (parent.y or 0) + GRID_DY
        elif steps:
            # Без явных координат кладём новый этап ниже всех существующих
            x, y = 0.0, max((s.y or 0) for s in steps) + GRID_DY
        else:
            x, y = 0.0, 0.0

    step = RoadmapStepModel(
        id=str(uuid.uuid4()), roadmap_id=roadmap_id, label=label,
        position=len(steps), x=x, y=y, done=False, color=color,
    )
    db.add(step)
    db.flush()
    if parent:
        db.add(RoadmapEdgeModel(id=str(uuid.uuid4()), roadmap_id=roadmap_id, from_id=parent.id, to_id=step.id))
    db.commit()
    db.refresh(r)
    return _roadmap_out(db, r)


def add_edge(db: Session, roadmap_id: str, from_id: str, to_id: str) -> RoadmapEdge | None:
    """None — если связь недопустима (тот же этап, чужой роадмап, дубликат)"""
    if from_id == to_id:
        return None
    ids = {s.id for s in db.query(RoadmapStepModel.id).filter(RoadmapStepModel.roadmap_id == roadmap_id).all()}
    if from_id not in ids or to_id not in ids:
        return None
    exists = db.query(RoadmapEdgeModel).filter(
        RoadmapEdgeModel.roadmap_id == roadmap_id,
        RoadmapEdgeModel.from_id == from_id, RoadmapEdgeModel.to_id == to_id,
    ).first()
    if exists:
        return None
    e = RoadmapEdgeModel(id=str(uuid.uuid4()), roadmap_id=roadmap_id, from_id=from_id, to_id=to_id)
    db.add(e)
    db.commit()
    return RoadmapEdge(id=e.id, from_id=e.from_id, to_id=e.to_id)


def delete_edge(db: Session, edge_id: str) -> bool:
    e = db.query(RoadmapEdgeModel).filter(RoadmapEdgeModel.id == edge_id).first()
    if not e:
        return False
    db.delete(e)
    db.commit()
    return True


def update_step(db: Session, step_id: str, updates: dict) -> RoadmapStepModel | None:
    step = db.query(RoadmapStepModel).filter(RoadmapStepModel.id == step_id).first()
    if not step:
        return None
    for key, value in updates.items():
        setattr(step, key, value)
    db.commit()
    db.refresh(step)
    return step


def delete_step(db: Session, step_id: str) -> bool:
    step = db.query(RoadmapStepModel).filter(RoadmapStepModel.id == step_id).first()
    if not step:
        return False
    roadmap_id = step.roadmap_id
    # Все стрелки, входящие в этап и исходящие из него, удаляются вместе с ним
    db.query(RoadmapEdgeModel).filter(
        (RoadmapEdgeModel.from_id == step_id) | (RoadmapEdgeModel.to_id == step_id)
    ).delete(synchronize_session=False)
    db.delete(step)
    db.commit()

    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if r and r.current_step_id == step_id:
        r.current_step_id = None
        db.commit()
    return True
