from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from achievements_models import AchievementModel, MetaModel, Achievement
import uuid
import logging

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_all(db: Session) -> list[Achievement]:
    rows = db.query(AchievementModel).order_by(AchievementModel.position, AchievementModel.created_at).all()
    return [Achievement.model_validate(r) for r in rows]


def create(db: Session, data: dict) -> Achievement:
    a = AchievementModel(
        id=str(uuid.uuid4()), created_at=_now(), done=False,
        position=db.query(AchievementModel).count(), **data,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return Achievement.model_validate(a)


def update(db: Session, achievement_id: str, updates: dict) -> Achievement | None:
    a = db.query(AchievementModel).filter(AchievementModel.id == achievement_id).first()
    if not a:
        return None
    for key, value in updates.items():
        if value is None and key == "title":
            continue
        setattr(a, key, value)
    if "done" in updates:
        a.done = bool(updates["done"])
        a.done_at = _now() if a.done else None
    db.commit()
    db.refresh(a)
    return Achievement.model_validate(a)


def delete(db: Session, achievement_id: str) -> bool:
    a = db.query(AchievementModel).filter(AchievementModel.id == achievement_id).first()
    if not a:
        return False
    db.delete(a)
    db.commit()
    return True


def import_legacy_unlocked(db: Session):
    """
    Разовый перенос старых автоматических достижений: уже разблокированные
    становятся выполненными достижениями нового модуля (чтобы данные не пропали).
    Сами старые таблицы не трогаем.
    """
    if db.query(MetaModel).filter(MetaModel.key == "legacy_achievements_imported").first():
        return
    tables = inspect(db.get_bind()).get_table_names()
    if "unlocked_achievements" in tables and "achievement_defs" in tables:
        rows = db.execute(text(
            "SELECT d.icon, d.title, d.description, u.unlocked_at "
            "FROM unlocked_achievements u JOIN achievement_defs d ON d.code = u.achievement_code "
            "ORDER BY u.unlocked_at"
        )).fetchall()
        base = db.query(AchievementModel).count()
        for i, (icon, title, desc, unlocked_at) in enumerate(rows):
            db.add(AchievementModel(
                id=str(uuid.uuid4()),
                title=f"{icon} {title}" if icon else title,
                description=desc, done=True,
                done_at=(unlocked_at or _now())[:19],
                position=base + i, created_at=(unlocked_at or _now())[:19],
            ))
        logger.info("Импортировано старых достижений: %d", len(rows))
    db.add(MetaModel(key="legacy_achievements_imported", value=_now()))
    db.commit()
