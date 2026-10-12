from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, Literal
from achievements_models import MetaModel
from database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

KEYS = {
    "theme": "setting_theme",
    "planner_mode": "setting_planner_mode",
    "dashboard_layout": "setting_dashboard_layout",
}


class Settings(BaseModel):
    theme: Optional[Literal["light", "dark"]] = None
    planner_mode: Optional[Literal["full", "free", "mixed"]] = None
    dashboard_layout: Optional[str] = Field(default=None, max_length=8000)  # JSON раскладки дашборда


def _read(db: Session) -> Settings:
    rows = {m.key: m.value for m in db.query(MetaModel).filter(MetaModel.key.in_(KEYS.values())).all()}
    return Settings(**{field: rows.get(key) for field, key in KEYS.items()})


@router.get("/", response_model=Settings)
def get_settings(db: Session = Depends(get_db)):
    return _read(db)


@router.put("/", response_model=Settings)
def put_settings(payload: Settings, db: Session = Depends(get_db)):
    for field, value in payload.model_dump(exclude_none=True).items():
        key = KEYS[field]
        row = db.query(MetaModel).filter(MetaModel.key == key).first()
        if row:
            row.value = value
        else:
            db.add(MetaModel(key=key, value=value))
    db.commit()
    return _read(db)
