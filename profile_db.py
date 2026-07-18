"""
Profile DB — логика XP, уровней, характеристик и достижений.

Основные функции:
- init_player(db) — создаёт игрока и 6 характеристик если их нет
- get_profile(db) — возвращает полный профиль
- award_xp(db, amount, stat_key) — начисляет XP (общий + в характеристику)
- check_and_unlock_achievements(db) — проверяет и разблокирует достижения
- recalculate_all(db) — пересчёт всех статов на основе истории (ретроактивно)
"""

from sqlalchemy.orm import Session
from datetime import datetime
from profile_models import (
    PlayerModel, StatModel, AchievementDefModel, UnlockedAchievementModel,
    PlayerProfile, Stat, Achievement, AchievementUnlockEvent
)
from profile_achievements import get_all_achievement_defs, check_all_achievements
import uuid


# ── Шесть характеристик ──

STAT_KEYS = ["strength", "health", "intelligence", "discipline", "wisdom", "charisma"]

STAT_LABELS = {
    "strength": "Сила",
    "health": "Здоровье",
    "intelligence": "Интеллект",
    "discipline": "Дисциплина",
    "wisdom": "Мудрость",
    "charisma": "Харизма",
}


def _xp_for_level(level: int) -> int:
    """Сколько суммарного XP нужно для достижения этого уровня"""
    # Формула: сумма от 1 до level-1 по level*100
    return level * (level + 1) // 2 * 100


def _level_from_xp(total_xp: int) -> int:
    """Определяет уровень по общему XP"""
    level = 1
    while _xp_for_level(level + 1) <= total_xp:
        level += 1
        if level >= 100:
            break
    return level


def _xp_to_next(total_xp: int, level: int) -> int:
    """Сколько XP осталось до следующего уровня"""
    needed = _xp_for_level(level + 1)
    return max(0, needed - total_xp)


def _stat_level_from_xp(stat_xp: int) -> int:
    """Уровень характеристики из её XP (та же формула)"""
    level = 1
    while (level * (level + 1) // 2 * 100) <= stat_xp:
        level += 1
        if level >= 100:
            break
    return level


# ── Инициализация ──

def init_player(db: Session) -> None:
    """Создаёт игрока и 6 характеристик если их ещё нет"""
    player = db.query(PlayerModel).first()
    if not player:
        player = PlayerModel(id=1, total_xp=0, level=1)
        db.add(player)

    for key in STAT_KEYS:
        stat = db.query(StatModel).filter(StatModel.stat_key == key).first()
        if not stat:
            db.add(StatModel(
                id=str(uuid.uuid4()),
                stat_key=key,
                xp=0,
                level=1
            ))

    # Засеваем справочник достижений
    existing_ach = db.query(AchievementDefModel).first()
    if not existing_ach:
        for ach_def in get_all_achievement_defs():
            db.add(AchievementDefModel(
                id=str(uuid.uuid4()),
                code=ach_def["code"],
                title=ach_def["title"],
                description=ach_def["description"],
                icon=ach_def["icon"],
                stat_key=ach_def.get("stat_key"),
                xp_reward=ach_def["xp_reward"],
            ))

    db.commit()


# Seed profile function removed to avoid test data in production
def _placeholder_seed_profile(): pass


# ── Получить профиль ──

def get_profile(db: Session) -> PlayerProfile:
    """Возвращает полный профиль игрока"""
    init_player(db)

    player = db.query(PlayerModel).first()
    stats = db.query(StatModel).all()

    stat_list = [
        Stat(
            stat_key=s.stat_key,
            xp=s.xp,
            level=_stat_level_from_xp(s.xp)
        )
        for s in stats
    ]
    # Сортируем в порядке STAT_KEYS
    stat_list.sort(key=lambda s: STAT_KEYS.index(s.stat_key) if s.stat_key in STAT_KEYS else 99)

    return PlayerProfile(
        total_xp=player.total_xp,
        level=_level_from_xp(player.total_xp),
        xp_to_next=_xp_to_next(player.total_xp, _level_from_xp(player.total_xp)),
        stats=stat_list,
    )


# ── Начисление XP ──

def award_xp(db: Session, amount: int, stat_key: str | None = None, commit: bool = True) -> dict:
    """
    Начисляет XP игроку.
    amount — общий XP
    stat_key — если указана, ещё начисляет amount XP в эту характеристику
    commit — если False, не делает db.commit() (для использования внутри транзакции)
    Возвращает dict с информацией о изменении уровня.
    """
    player = db.query(PlayerModel).first()
    if not player:
        init_player(db)
        player = db.query(PlayerModel).first()

    old_level = _level_from_xp(player.total_xp)
    player.total_xp += amount
    new_level = _level_from_xp(player.total_xp)
    player.level = new_level

    stat_xp_gained = 0
    if stat_key:
        stat = db.query(StatModel).filter(StatModel.stat_key == stat_key).first()
        if stat:
            stat.xp += amount
            stat.level = _stat_level_from_xp(stat.xp)
            stat_xp_gained = amount

    if commit:
        db.commit()

    return {
        "xp_gained": amount,
        "total_xp": player.total_xp,
        "level": new_level,
        "level_up": new_level > old_level,
        "stat_key": stat_key,
        "stat_label": STAT_LABELS.get(stat_key) if stat_key else None,
        "stat_xp_gained": stat_xp_gained,
    }


def revoke_xp(db: Session, amount: int, stat_key: str | None = None, commit: bool = True) -> dict:
    """
    Отнимает XP у игрока (например, при отмене чека привычки).
    amount — общий XP
    stat_key — если указана, ещё отнимает amount XP из этой характеристики
    commit — если False, не делает db.commit() (для использования внутри транзакции)
    Возвращает dict с информацией об изменении.
    """
    player = db.query(PlayerModel).first()
    if not player:
        return {"xp_revoked": 0}

    old_level = _level_from_xp(player.total_xp)
    player.total_xp = max(0, player.total_xp - amount)
    new_level = _level_from_xp(player.total_xp)
    player.level = new_level

    stat_xp_revoked = 0
    if stat_key:
        stat = db.query(StatModel).filter(StatModel.stat_key == stat_key).first()
        if stat:
            stat.xp = max(0, stat.xp - amount)
            stat.level = _stat_level_from_xp(stat.xp)
            stat_xp_revoked = amount

    if commit:
        db.commit()

    return {
        "xp_revoked": amount,
        "total_xp": player.total_xp,
        "level": new_level,
        "level_down": new_level < old_level,
        "stat_key": stat_key,
        "stat_label": STAT_LABELS.get(stat_key) if stat_key else None,
        "stat_xp_revoked": stat_xp_revoked,
    }


# ── Достижения ──

def get_unlocked_achievements(db: Session) -> list[Achievement]:
    """Возвращает список разблокированных достижений"""
    unlocked = db.query(UnlockedAchievementModel).order_by(
        UnlockedAchievementModel.unlocked_at.desc()
    ).all()

    result = []
    for ua in unlocked:
        ach_def = db.query(AchievementDefModel).filter(
            AchievementDefModel.code == ua.achievement_code
        ).first()
        if ach_def:
            result.append(Achievement(
                code=ach_def.code,
                title=ach_def.title,
                description=ach_def.description,
                icon=ach_def.icon,
                stat_key=ach_def.stat_key,
                xp_reward=ach_def.xp_reward,
                unlocked_at=ua.unlocked_at,
            ))
    return result


def check_and_unlock_achievements(db: Session) -> list[AchievementUnlockEvent]:
    """
    Проверяет все достижения и разблокирует новые.
    Возвращает список событий разблокировки.
    """
    init_player(db)

    already_unlocked = set(
        ua.achievement_code
        for ua in db.query(UnlockedAchievementModel).all()
    )

    new_unlocks = check_all_achievements(db, already_unlocked)
    events = []

    for ach in new_unlocks:
        # Re-check: может быть уже разблокировано другим запросом
        existing = db.query(UnlockedAchievementModel).filter(
            UnlockedAchievementModel.achievement_code == ach["code"]
        ).first()
        if existing:
            continue

        # Сохраняем в БД (без commit — делаем один общий в конце)
        ua = UnlockedAchievementModel(
            id=str(uuid.uuid4()),
            achievement_code=ach["code"],
            unlocked_at=datetime.now().isoformat(),
        )
        db.add(ua)

        # Начисляем XP (без commit)
        try:
            xp_result = award_xp(db, ach["xp_reward"], ach.get("stat_key"), commit=False)
        except Exception:
            db.rollback()
            continue

        events.append(AchievementUnlockEvent(
            achievement=Achievement(
                code=ach["code"],
                title=ach["title"],
                description=ach["description"],
                icon=ach["icon"],
                stat_key=ach.get("stat_key"),
                xp_reward=ach["xp_reward"],
                unlocked_at=ua.unlocked_at,
            ),
            xp_gained=ach["xp_reward"],
            stat_gained=ach.get("stat_key"),
            stat_xp_gained=ach.get("stat_xp", 0),
        ))

    db.commit()
    return events


# ── Ретроактивный пересчёт ──

def recalculate_all(db: Session) -> PlayerProfile:
    """
    Полный пересчёт профиля на основе истории.
    Вызывается при первом открытии профиля или по запросу.
    Сбрасывает XP и пересчитывает из существующих данных.
    """
    init_player(db)

    # Сброс
    player = db.query(PlayerModel).first()
    player.total_xp = 0
    player.level = 1

    stats = {s.stat_key: s for s in db.query(StatModel).all()}
    for s in stats.values():
        s.xp = 0
        s.level = 1

    # Считаем XP из тренировок
    from workouts_models import WorkoutModel
    workout_count = db.query(WorkoutModel).count()
    _add_stat_xp(stats, "strength", workout_count * 25)

    # Считаем XP из хороших привычек
    from habits_models import CheckModel, HabitModel
    good_checks = db.query(CheckModel).join(
        HabitModel, CheckModel.habit_id == HabitModel.id
    ).filter(HabitModel.kind == "good").count()
    _add_stat_xp(stats, "health", good_checks * 10)

    # Задачи rest → здоровье
    from models import TaskModel
    rest_done = db.query(TaskModel).filter(
        TaskModel.task_type == "rest", TaskModel.status == "done"
    ).count()
    _add_stat_xp(stats, "health", rest_done * 15)

    # study + work → интеллект
    study_done = db.query(TaskModel).filter(
        TaskModel.task_type == "study", TaskModel.status == "done"
    ).count()
    work_done = db.query(TaskModel).filter(
        TaskModel.task_type == "work", TaskModel.status == "done"
    ).count()
    _add_stat_xp(stats, "intelligence", (study_done + work_done) * 15)

    # routine → дисциплина
    routine_done = db.query(TaskModel).filter(
        TaskModel.task_type == "routine", TaskModel.status == "done"
    ).count()
    _add_stat_xp(stats, "discipline", routine_done * 15)

    # Финансы → мудрость
    from finance_models import TransactionModel, DebtModel
    from sqlalchemy import func
    income = db.query(func.coalesce(func.sum(TransactionModel.amount), 0)).filter(
        TransactionModel.transaction_type == "income"
    ).scalar() or 0
    expense = db.query(func.coalesce(func.sum(TransactionModel.amount), 0)).filter(
        TransactionModel.transaction_type == "expense"
    ).scalar() or 0
    if float(income) > float(expense):
        _add_stat_xp(stats, "wisdom", 100)

    paid_owe = db.query(DebtModel).filter(
        DebtModel.direction == "owe", DebtModel.status == "paid"
    ).count()
    _add_stat_xp(stats, "wisdom", paid_owe * 40)

    # personal → харизма
    personal_done = db.query(TaskModel).filter(
        TaskModel.task_type == "personal", TaskModel.status == "done"
    ).count()
    _add_stat_xp(stats, "charisma", personal_done * 15)

    # owed paid → харизма
    paid_owed = db.query(DebtModel).filter(
        DebtModel.direction == "owed", DebtModel.status == "paid"
    ).count()
    _add_stat_xp(stats, "charisma", paid_owed * 40)

    # Обновляем уровни характеристик
    for s in stats.values():
        s.level = _stat_level_from_xp(s.xp)

    # Общий XP = сумма всех stat XP
    player.total_xp = sum(s.xp for s in stats.values())
    player.level = _level_from_xp(player.total_xp)

    # Добавляем XP за уже разблокированные достижения (чтобы не потерять при пересчёте)
    existing_unlocks = db.query(UnlockedAchievementModel).all()
    for ua in existing_unlocks:
        ach_def = db.query(AchievementDefModel).filter(
            AchievementDefModel.code == ua.achievement_code
        ).first()
        if ach_def:
            player.total_xp += ach_def.xp_reward
            if ach_def.stat_key and ach_def.stat_key in stats:
                stats[ach_def.stat_key].xp += ach_def.xp_reward
                stats[ach_def.stat_key].level = _stat_level_from_xp(stats[ach_def.stat_key].xp)

    # Пересчитываем уровни после добавления XP достижений
    player.level = _level_from_xp(player.total_xp)

    db.commit()

    return get_profile(db)


def _add_stat_xp(stats: dict, key: str, amount: int):
    """Добавляет XP в характеристику (вспомогательная)"""
    if key in stats and amount > 0:
        stats[key].xp += amount


# ── Сброс профиля ──

def reset_profile(db: Session) -> PlayerProfile:
    """
    Полный сброс профиля: XP, уровни, статы, достижения.
    Используется для очистки тестовых данных.
    """
    # Сброс игрока
    player = db.query(PlayerModel).first()
    if player:
        player.total_xp = 0
        player.level = 1

    # Сброс статов
    for stat in db.query(StatModel).all():
        stat.xp = 0
        stat.level = 1

    # Удаление разблокированных достижений
    db.query(UnlockedAchievementModel).delete()

    db.commit()
    return get_profile(db)
