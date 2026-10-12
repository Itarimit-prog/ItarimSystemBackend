from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from recurring_models import RecurringRule, RecurringCreate, RecurringUpdate
from database import get_db
import recurring_db

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("/", response_model=list[RecurringRule])
def get_rules(db: Session = Depends(get_db)):
    return recurring_db.get_all_rules(db)


@router.post("/", response_model=RecurringRule, status_code=201)
def create_rule(payload: RecurringCreate, db: Session = Depends(get_db)):
    return recurring_db.create_rule(db, payload.model_dump())


@router.patch("/{rule_id}", response_model=RecurringRule)
def update_rule(rule_id: str, payload: RecurringUpdate, db: Session = Depends(get_db)):
    updated = recurring_db.update_rule(db, rule_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    return updated


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    if not recurring_db.delete_rule(db, rule_id):
        raise HTTPException(status_code=404, detail="Правило не найдено")
