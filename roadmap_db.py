from sqlalchemy.orm import Session
from roadmap_models import RoadmapModel, RoadmapStepModel, Roadmap, RoadmapStep
import uuid


def _roadmap_out(db: Session, r: RoadmapModel) -> Roadmap:
    steps = db.query(RoadmapStepModel).filter(
        RoadmapStepModel.roadmap_id == r.id
    ).order_by(RoadmapStepModel.position).all()
    return Roadmap(
        id=r.id,
        name=r.name,
        position=r.position,
        current_step_id=r.current_step_id,
        steps=[RoadmapStep(id=s.id, label=s.label, position=s.position) for s in steps]
    )


def get_all_roadmaps(db: Session) -> list[Roadmap]:
    roadmaps = db.query(RoadmapModel).order_by(RoadmapModel.position).all()
    return [_roadmap_out(db, r) for r in roadmaps]


def create_roadmap(db: Session, name: str) -> Roadmap:
    position = db.query(RoadmapModel).count()
    r = RoadmapModel(id=str(uuid.uuid4()), name=name, position=position)
    db.add(r)
    db.commit()
    db.refresh(r)
    return _roadmap_out(db, r)


def update_roadmap(db: Session, roadmap_id: str, updates: dict) -> Roadmap | None:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if not r:
        return None
    for key, value in updates.items():
        if value is not None:
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


def add_step(db: Session, roadmap_id: str, label: str) -> Roadmap | None:
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if not r:
        return None
    position = db.query(RoadmapStepModel).filter(RoadmapStepModel.roadmap_id == roadmap_id).count()
    step = RoadmapStepModel(id=str(uuid.uuid4()), roadmap_id=roadmap_id, label=label, position=position)
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
        if value is not None:
            setattr(step, key, value)
    db.commit()
    db.refresh(step)
    return step


def delete_step(db: Session, step_id: str) -> bool:
    step = db.query(RoadmapStepModel).filter(RoadmapStepModel.id == step_id).first()
    if not step:
        return False
    roadmap_id = step.roadmap_id
    db.delete(step)
    db.commit()

    # Если удалили текущий шаг — снимаем метку "Ты тут" с roadmap
    r = db.query(RoadmapModel).filter(RoadmapModel.id == roadmap_id).first()
    if r and r.current_step_id == step_id:
        r.current_step_id = None
        db.commit()

    return True
