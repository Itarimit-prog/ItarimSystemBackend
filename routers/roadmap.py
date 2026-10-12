from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from roadmap_models import (
    Roadmap, RoadmapCreate, RoadmapUpdate, RoadmapStepCreate, RoadmapStepUpdate,
    RoadmapEdge, RoadmapEdgeCreate,
)
from database import get_db
import roadmap_db

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


@router.get("/", response_model=list[Roadmap])
def get_roadmaps(db: Session = Depends(get_db)):
    return roadmap_db.get_all_roadmaps(db)


@router.post("/", response_model=Roadmap, status_code=201)
def create_roadmap(payload: RoadmapCreate, db: Session = Depends(get_db)):
    return roadmap_db.create_roadmap(db, payload.name)


@router.patch("/{roadmap_id}", response_model=Roadmap)
def update_roadmap(roadmap_id: str, payload: RoadmapUpdate, db: Session = Depends(get_db)):
    updated = roadmap_db.update_roadmap(db, roadmap_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Roadmap не найден")
    return updated


@router.delete("/{roadmap_id}", status_code=204)
def delete_roadmap(roadmap_id: str, db: Session = Depends(get_db)):
    if not roadmap_db.delete_roadmap(db, roadmap_id):
        raise HTTPException(status_code=404, detail="Roadmap не найден")


@router.post("/{roadmap_id}/steps", response_model=Roadmap, status_code=201)
def add_step(roadmap_id: str, payload: RoadmapStepCreate, db: Session = Depends(get_db)):
    updated = roadmap_db.add_step(db, roadmap_id, payload.label, payload.parent_step_id, payload.x, payload.y, payload.color)
    if not updated:
        raise HTTPException(status_code=404, detail="Roadmap не найден")
    return updated


@router.patch("/steps/{step_id}")
def update_step(step_id: str, payload: RoadmapStepUpdate, db: Session = Depends(get_db)):
    updated = roadmap_db.update_step(db, step_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Этап не найден")
    return roadmap_db._step_out(updated)


@router.delete("/steps/{step_id}", status_code=204)
def delete_step(step_id: str, db: Session = Depends(get_db)):
    if not roadmap_db.delete_step(db, step_id):
        raise HTTPException(status_code=404, detail="Этап не найден")


@router.post("/{roadmap_id}/edges", response_model=RoadmapEdge, status_code=201)
def add_edge(roadmap_id: str, payload: RoadmapEdgeCreate, db: Session = Depends(get_db)):
    edge = roadmap_db.add_edge(db, roadmap_id, payload.from_id, payload.to_id)
    if not edge:
        raise HTTPException(status_code=400, detail="Нельзя создать такую связь")
    return edge


@router.delete("/edges/{edge_id}", status_code=204)
def delete_edge(edge_id: str, db: Session = Depends(get_db)):
    if not roadmap_db.delete_edge(db, edge_id):
        raise HTTPException(status_code=404, detail="Связь не найдена")
