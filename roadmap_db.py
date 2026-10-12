from sqlalchemy.orm import Session
from roadmap_models import RoadmapModel, RoadmapStepModel, Roadmap, RoadmapStep
import uuid

# Шаг сетки при автоматической раскладке узлов на канвасе
GRID_DX = 240
GRID_DY = 130


def _step_out(s: RoadmapStepModel) -> RoadmapStep:
    return RoadmapStep(
        id=s.id, label=s.label, position=s.position,
        x=s.x or 0, y=s.y or 0,
        parent_step_id=s.parent_step_id, done=bool(s.done),
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
    db.delete(r)
    db.commit()
    return True


def delete_roadmaps_of_goal(db: Session, goal_id: str):
    for r in db.query(RoadmapModel).filter(RoadmapModel.goal_id == goal_id).all():
        db.query(RoadmapStepModel).filter(RoadmapStepModel.roadmap_id == r.id).delete()
        db.delete(r)
    db.commit()


def add_step(
    db: Session, roadmap_id: str, label: str,
    parent_step_id: str | None = None, x: float | None = None, y: float | None = None,
) -> Roadmap | None:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if not r:
        return None
    steps = db.query(RoadmapStepModel).filter(
        RoadmapStepModel.roadmap_id == roadmap_id
    ).order_by(RoadmapStepModel.position).all()

    # Если родитель не указан — продолжаем цепочку от последнего узла
    parent = None
    if parent_step_id:
        parent = next((s for s in steps if s.id == parent_step_id), None)
    elif steps:
        parent = steps[-1]

    if x is None or y is None:
        if parent:
            siblings = sum(1 for s in steps if s.parent_step_id == parent.id)
            x = (parent.x or 0) + siblings * GRID_DX
            y = (parent.y or 0) + GRID_DY
        else:
            x, y = 0.0, 0.0

    step = RoadmapStepModel(
        id=str(uuid.uuid4()), roadmap_id=roadmap_id, label=label,
        position=len(steps), x=x, y=y,
        parent_step_id=parent.id if parent else None, done=False,
    )
    db.add(step)
    # Первый добавленный шаг сразу становится текущим
    if not r.current_step_id:
        db.flush()
        r.current_step_id = step.id
    db.commit()
    db.refresh(r)
    return _roadmap_out(db, r)


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
    # Дочерние узлы переподвешиваем к родителю удаляемого, чтобы граф не рассыпался
    db.query(RoadmapStepModel).filter(
        RoadmapStepModel.parent_step_id == step_id
    ).update({RoadmapStepModel.parent_step_id: step.parent_step_id})
    db.delete(step)
    db.commit()

    # Если удалили текущий шаг — снимаем метку "Ты тут" с roadmap
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if r and r.current_step_id == step_id:
        r.current_step_id = None
        db.commit()

    return True
