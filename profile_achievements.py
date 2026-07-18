"""
Определения достижений (~150 штук).

Каждое достижение:
- code, title, description, icon, stat_key, xp_reward, stat_xp
- check(db) -> bool: функция проверки
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta


# ════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ЗАПРОСЫ
# ════════════════════════════════════════

def _count_workouts(db: Session) -> int:
    from workouts_models import WorkoutModel
    return db.query(func.count(WorkoutModel.id)).scalar() or 0


def _total_workout_minutes(db: Session) -> int:
    from workouts_models import WorkoutModel
    return db.query(func.coalesce(func.sum(WorkoutModel.duration_minutes), 0)).scalar() or 0


def _count_tasks_done(db: Session, task_type: str | None = None) -> int:
    from models import TaskModel
    q = db.query(func.count(TaskModel.id)).filter(TaskModel.status == "done")
    if task_type:
        q = q.filter(TaskModel.task_type == task_type)
    return q.scalar() or 0


def _count_good_habit_checks(db: Session) -> int:
    from habits_models import CheckModel, HabitModel
    return db.query(func.count(CheckModel.id)).join(
        HabitModel, CheckModel.habit_id == HabitModel.id
    ).filter(HabitModel.kind == "good").scalar() or 0


def _count_good_habits(db: Session) -> int:
    from habits_models import HabitModel
    return db.query(func.count(HabitModel.id)).filter(HabitModel.kind == "good").scalar() or 0


def _count_bad_habits(db: Session) -> int:
    from habits_models import HabitModel
    return db.query(func.count(HabitModel.id)).filter(HabitModel.kind == "bad").scalar() or 0


def _unique_habit_check_days(db: Session) -> int:
    from habits_models import CheckModel, HabitModel
    return db.query(func.count(func.distinct(CheckModel.date))).join(
        HabitModel, CheckModel.habit_id == HabitModel.id
    ).filter(HabitModel.kind == "good").scalar() or 0


def _max_consecutive_habit_days(db: Session) -> int:
    """Максимальная серия последовательных дней с хорошими привычками"""
    from habits_models import CheckModel, HabitModel
    dates = db.query(func.distinct(CheckModel.date)).join(
        HabitModel, CheckModel.habit_id == HabitModel.id
    ).filter(HabitModel.kind == "good").order_by(CheckModel.date).all()
    if not dates:
        return 0
    date_list = sorted([datetime.strptime(d[0], "%Y-%m-%d").date() for d in dates])
    max_streak = 1
    current = 1
    for i in range(1, len(date_list)):
        if (date_list[i] - date_list[i - 1]).days == 1:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 1
    return max_streak


def _max_streak_days(db: Session) -> int:
    """Максимальная серия дней без срыва (только если есть плохие привычки)"""
    from habits_models import RelapseModel, HabitModel
    bad_habits = db.query(HabitModel).filter(HabitModel.kind == "bad").all()
    if not bad_habits:
        return 0  # нет плохих привычек — серия не считается

    max_gap = 0
    for h in bad_habits:
        relapses = db.query(RelapseModel).filter(
            RelapseModel.habit_id == h.id
        ).order_by(RelapseModel.timestamp).all()

        if not relapses:
            # Есть плохая привычка, но срывов нет — не считаем (нет данных)
            continue

        timestamps = [datetime.fromisoformat(r.timestamp) for r in relapses]
        timestamps.sort()

        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i - 1]).days
            max_gap = max(max_gap, gap)

        current_gap = (datetime.now(timezone.utc).replace(tzinfo=None) - timestamps[-1]).days
        max_gap = max(max_gap, current_gap)

    return max_gap


def _count_paid_debts(db: Session, direction: str) -> int:
    from finance_models import DebtModel
    return db.query(func.count(DebtModel.id)).filter(
        DebtModel.direction == direction, DebtModel.status == "paid"
    ).scalar() or 0


def _count_all_debts(db: Session, direction: str, status: str | None = None) -> int:
    from finance_models import DebtModel
    q = db.query(func.count(DebtModel.id)).filter(DebtModel.direction == direction)
    if status:
        q = q.filter(DebtModel.status == status)
    return q.scalar() or 0


def _total_income(db: Session) -> float:
    from finance_models import TransactionModel
    return float(db.query(func.coalesce(func.sum(TransactionModel.amount), 0)).filter(
        TransactionModel.transaction_type == "income"
    ).scalar() or 0)


def _total_transactions(db: Session, t_type: str | None = None) -> int:
    from finance_models import TransactionModel
    q = db.query(func.count(TransactionModel.id))
    if t_type:
        q = q.filter(TransactionModel.transaction_type == t_type)
    return q.scalar() or 0


def _is_profitable_month(db: Session) -> bool:
    from finance_models import TransactionModel
    now = datetime.now()
    month_start = now.replace(day=1).strftime("%Y-%m-%d")
    month_end = now.strftime("%Y-%m-%d")
    income = db.query(func.coalesce(func.sum(TransactionModel.amount), 0)).filter(
        TransactionModel.transaction_type == "income",
        TransactionModel.date >= month_start,
        TransactionModel.date <= month_end
    ).scalar() or 0
    expense = db.query(func.coalesce(func.sum(TransactionModel.amount), 0)).filter(
        TransactionModel.transaction_type == "expense",
        TransactionModel.date >= month_start,
        TransactionModel.date <= month_end
    ).scalar() or 0
    return float(income) > float(expense) and float(income) > 0


def _count_all_owe_paid(db: Session) -> bool:
    from finance_models import DebtModel
    paid = db.query(func.count(DebtModel.id)).filter(
        DebtModel.direction == "owe", DebtModel.status == "paid"
    ).scalar() or 0
    active = db.query(func.count(DebtModel.id)).filter(
        DebtModel.direction == "owe", DebtModel.status == "active"
    ).scalar() or 0
    return paid > 0 and active == 0


def _player_level(db: Session) -> int:
    from profile_models import PlayerModel
    p = db.query(PlayerModel).first()
    if not p:
        return 1
    total = p.total_xp
    level = 1
    while (level * (level + 1) // 2 * 100) <= total:
        level += 1
        if level >= 100:
            break
    return level


def _stat_level(db: Session, key: str) -> int:
    from profile_models import StatModel
    s = db.query(StatModel).filter(StatModel.stat_key == key).first()
    if not s:
        return 1
    xp = s.xp
    level = 1
    while (level * (level + 1) // 2 * 100) <= xp:
        level += 1
        if level >= 100:
            break
    return level


def _unlocked_count(db: Session) -> int:
    from profile_models import UnlockedAchievementModel
    return db.query(func.count(UnlockedAchievementModel.id)).scalar() or 0


# ════════════════════════════════════════
#  BATCH ГЕНЕРАТОРЫ ДОСТИЖЕНИЙ
# ════════════════════════════════════════

# Пороги прогресса: (порог, суффикс_звания, XP, stat_XP)
_TIERS = [
    (1, "Новичок", 20, 15),
    (3, "Ученик", 30, 20),
    (5, "Знающий", 40, 25),
    (10, "Опытный", 60, 40),
    (25, "Умелый", 80, 50),
    (50, "Мастер", 120, 75),
    (75, "Эксперт", 150, 95),
    (100, "Виртуоз", 180, 115),
    (150, "Грандмастер", 220, 140),
    (200, "Легенда", 280, 180),
    (300, "Мифический", 350, 220),
    (500, "Божество", 500, 320),
    (750, "Трансцендент", 650, 420),
    (1000, "Абсолют", 800, 520),
]

_ICONS = {
    "strength": "💪", "health": "❤️", "intelligence": "🧠",
    "discipline": "⚡", "wisdom": "💰", "charisma": "😊", None: "⭐",
}

_LABELS = {
    "strength": "Сила", "health": "Здоровье", "intelligence": "Интеллект",
    "discipline": "Дисциплина", "wisdom": "Мудрость", "charisma": "Харизма",
}


def _batch(code_prefix, title_template, desc_template, stat_key, check_fn, tiers=_TIERS):
    """Генерирует список достижений по порогам."""
    result = []
    for threshold, suffix, xp, stat_xp in tiers:
        result.append({
            "code": f"{code_prefix}_{threshold}",
            "title": title_template.format(suffix=suffix, n=threshold),
            "description": desc_template.format(n=threshold),
            "icon": _ICONS.get(stat_key, "⭐"),
            "stat_key": stat_key,
            "xp_reward": xp,
            "stat_xp": stat_xp,
            "check": lambda db, fn=check_fn, t=threshold: fn(db) >= t,
        })
    return result


# ════════════════════════════════════════
#  СПИСОК ВСЕХ ДОСТИЖЕНИЙ (~150)
# ════════════════════════════════════════

ACHIEVEMENTS: list[dict] = []

# ──── СИЛА (strength) ──── ~19
ACHIEVEMENTS += _batch(
    "workouts", "{suffix}", "Завершить {n} тренировок",
    "strength", _count_workouts
)
ACHIEVEMENTS += _batch(
    "workout_mins", "{suffix} выносливости", "Накопить {n} минут тренировок",
    "strength", _total_workout_minutes,
    [(30, "Разминка", 20, 15), (60, "Час силы", 40, 25), (120, "Два часа", 60, 40),
     (300, "Пять часов", 100, 65), (600, "Десять часов", 150, 95),
     (1200, "Двадцать часов", 250, 160), (2400, "Сорок часов", 400, 260),
     (4800, "Восемьдесят часов", 600, 390)]
)
ACHIEVEMENTS += [
    {"code": "strength_lv5", "title": "Крепкий", "description": "Сила достигла 5 уровня",
     "icon": "💪", "stat_key": "strength", "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "strength") >= 5},
    {"code": "strength_lv10", "title": "Могучий", "description": "Сила достигла 10 уровня",
     "icon": "💪", "stat_key": "strength", "xp_reward": 250, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "strength") >= 10},
    {"code": "strength_lv25", "title": "Титан", "description": "Сила достигла 25 уровня",
     "icon": "💪", "stat_key": "strength", "xp_reward": 500, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "strength") >= 25},
]

# ──── ЗДОРОВЬЕ (health) ──── ~25
ACHIEVEMENTS += _batch(
    "habits", "{suffix} здоровья", "Выполнить {n} хороших привычек",
    "health", _count_good_habit_checks
)
ACHIEVEMENTS += _batch(
    "rest_tasks", "{suffix} отдыха", "Выполнить {n} задач типа 'отдых'",
    "health", lambda db: _count_tasks_done(db, "rest"),
    [(1, "Пауза", 20, 15), (3, "Передышка", 30, 20), (5, "Расслабление", 40, 25),
     (10, "Мастер отдыха", 60, 40), (25, "Дзен", 100, 65),
     (50, "Гармония", 150, 95), (100, "Нирвана", 250, 160)]
)
ACHIEVEMENTS += _batch(
    "habit_days", "{suffix} постоянства", "Отметить привычки в {n} разных дней",
    "health", _unique_habit_check_days,
    [(1, "Первый день", 20, 15), (3, "Три дня", 30, 20), (7, "Неделя", 50, 35),
     (14, "Две недели", 80, 50), (30, "Месяц", 150, 95),
     (60, "Два месяца", 250, 160), (90, "Три месяца", 400, 260),
     (180, "Полгода", 600, 390), (365, "Год", 1000, 650)]
)
ACHIEVEMENTS += _batch(
    "habit_streak", "{suffix} серия", "Серия привычек {n} дней подряд",
    "health", _max_consecutive_habit_days,
    [(3, "Три дня", 30, 20), (7, "Неделя", 60, 40), (14, "Две недели", 100, 65),
     (30, "Месяц", 200, 130), (60, "Два месяца", 350, 225),
     (90, "Три месяца", 500, 325), (180, "Полгода", 800, 520)]
)
ACHIEVEMENTS += [
    {"code": "good_habits_3", "title": "ЗОЖ-набор", "description": "Создать 3 хорошие привычки",
     "icon": "❤️", "stat_key": "health", "xp_reward": 40, "stat_xp": 25,
     "check": lambda db: _count_good_habits(db) >= 3},
    {"code": "good_habits_5", "title": "Полный ЗОЖ", "description": "Создать 5 хороших привычек",
     "icon": "❤️", "stat_key": "health", "xp_reward": 80, "stat_xp": 50,
     "check": lambda db: _count_good_habits(db) >= 5},
    {"code": "health_lv5", "title": "Бодрый", "description": "Здоровье достигло 5 уровня",
     "icon": "❤️", "stat_key": "health", "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "health") >= 5},
    {"code": "health_lv10", "title": "Здоровяк", "description": "Здоровье достигло 10 уровня",
     "icon": "❤️", "stat_key": "health", "xp_reward": 250, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "health") >= 10},
]

# ──── ИНТЕЛЛЕКТ (intelligence) ──── ~23
ACHIEVEMENTS += _batch(
    "study", "{suffix} знаний", "Выполнить {n} учебных задач",
    "intelligence", lambda db: _count_tasks_done(db, "study")
)
ACHIEVEMENTS += _batch(
    "work", "{suffix} труда", "Выполнить {n} рабочих задач",
    "intelligence", lambda db: _count_tasks_done(db, "work")
)
ACHIEVEMENTS += [
    {"code": "int_combo_5", "title": "Эрудит", "description": "5 учебных + 5 рабочих задач",
     "icon": "🧠", "stat_key": "intelligence", "xp_reward": 80, "stat_xp": 50,
     "check": lambda db: _count_tasks_done(db, "study") >= 5 and _count_tasks_done(db, "work") >= 5},
    {"code": "int_combo_25", "title": "Мастер ума", "description": "25 учебных + 25 рабочих задач",
     "icon": "🧠", "stat_key": "intelligence", "xp_reward": 200, "stat_xp": 130,
     "check": lambda db: _count_tasks_done(db, "study") >= 25 and _count_tasks_done(db, "work") >= 25},
    {"code": "int_lv5", "title": "Умник", "description": "Интеллект достиг 5 уровня",
     "icon": "🧠", "stat_key": "intelligence", "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "intelligence") >= 5},
    {"code": "int_lv10", "title": "Гений", "description": "Интеллект достиг 10 уровня",
     "icon": "🧠", "stat_key": "intelligence", "xp_reward": 250, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "intelligence") >= 10},
    {"code": "int_lv25", "title": "Мудрец", "description": "Интеллект достиг 25 уровня",
     "icon": "🧠", "stat_key": "intelligence", "xp_reward": 500, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "intelligence") >= 25},
]

# ──── ДИСЦИПЛИНА (discipline) ──── ~24
ACHIEVEMENTS += _batch(
    "streak", "{suffix} воли", "{n} дней без срыва",
    "discipline", _max_streak_days,
    [(3, "Три дня", 30, 20), (7, "Неделя", 50, 35), (14, "Две недели", 80, 50),
     (21, "Три недели", 120, 75), (30, "Месяц", 200, 130),
     (60, "Два месяца", 350, 225), (90, "Три месяца", 500, 325),
     (180, "Полгода", 800, 520), (365, "Год", 1200, 780)]
)
ACHIEVEMENTS += _batch(
    "routine", "{suffix} порядка", "Выполнить {n} рутинных задач",
    "discipline", lambda db: _count_tasks_done(db, "routine")
)
ACHIEVEMENTS += [
    {"code": "bad_habits_3", "title": "Борец", "description": "Создать 3 плохие привычки для контроля",
     "icon": "⚡", "stat_key": "discipline", "xp_reward": 30, "stat_xp": 20,
     "check": lambda db: _count_bad_habits(db) >= 3},
    {"code": "bad_habits_5", "title": "Под контролем", "description": "Отслеживать 5 плохих привычек",
     "icon": "⚡", "stat_key": "discipline", "xp_reward": 60, "stat_xp": 40,
     "check": lambda db: _count_bad_habits(db) >= 5},
    {"code": "discipline_lv5", "title": "Организованный", "description": "Дисциплина достигла 5 уровня",
     "icon": "⚡", "stat_key": "discipline", "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "discipline") >= 5},
    {"code": "discipline_lv10", "title": "Несгибаемый", "description": "Дисциплина достигла 10 уровня",
     "icon": "⚡", "stat_key": "discipline", "xp_reward": 250, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "discipline") >= 10},
    {"code": "discipline_lv25", "title": "Стальной", "description": "Дисциплина достигла 25 уровня",
     "icon": "⚡", "stat_key": "discipline", "xp_reward": 500, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "discipline") >= 25},
]

# ──── МУДРОСТЬ (wisdom) ──── ~23
ACHIEVEMENTS += _batch(
    "income_txns", "{suffix} дохода", "Совершить {n} операций дохода",
    "wisdom", lambda db: _total_transactions(db, "income"),
    [(1, "Первый доход", 20, 15), (5, "Пять поступлений", 40, 25),
     (10, "Десять поступлений", 60, 40), (25, "Двадцать пять", 100, 65),
     (50, "Полсотни", 150, 95), (100, "Сотня доходов", 250, 160)]
)
ACHIEVEMENTS += _batch(
    "total_income", "{suffix} капитала", "Заработать {n} суммарно",
    "wisdom", lambda db: int(_total_income(db)),
    [(500, "Первые деньги", 30, 20), (1000, "Тысяча", 60, 40),
     (3000, "Три тысячи", 100, 65), (5000, "Пять тысяч", 150, 95),
     (10000, "Десять тысяч", 250, 160), (25000, "Двадцать пять тысяч", 400, 260),
     (50000, "Пятьдесят тысяч", 600, 390), (100000, "Сто тысяч", 1000, 650)]
)
ACHIEVEMENTS += _batch(
    "debts_paid", "{suffix} долгов", "Выплатить {n} своих долгов",
    "wisdom", lambda db: _count_paid_debts(db, "owe"),
    [(1, "Первый долг", 30, 20), (3, "Три долга", 60, 40),
     (5, "Пять долгов", 100, 65), (10, "Десять долгов", 200, 130)]
)
ACHIEVEMENTS += [
    {"code": "profitable_month", "title": "В плюсе", "description": "Закрыть месяц в плюсе",
     "icon": "📈", "stat_key": "wisdom", "xp_reward": 100, "stat_xp": 60,
     "check": lambda db: _is_profitable_month(db)},
    {"code": "debt_free", "title": "Свободен", "description": "Выплатить ВСЕ свои долги",
     "icon": "🕊️", "stat_key": "wisdom", "xp_reward": 200, "stat_xp": 130,
     "check": lambda db: _count_all_owe_paid(db)},
    {"code": "expense_tracker", "title": "Учётчик", "description": "Записать 50 операций расхода",
     "icon": "📝", "stat_key": "wisdom", "xp_reward": 80, "stat_xp": 50,
     "check": lambda db: _total_transactions(db, "expense") >= 50},
    {"code": "wisdom_lv5", "title": "Расчётливый", "description": "Мудрость достигла 5 уровня",
     "icon": "💰", "stat_key": "wisdom", "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "wisdom") >= 5},
    {"code": "wisdom_lv10", "title": "Финансовый гуру", "description": "Мудрость достигла 10 уровня",
     "icon": "💰", "stat_key": "wisdom", "xp_reward": 250, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "wisdom") >= 10},
]

# ──── ХАРИЗМА (charisma) ──── ~22
ACHIEVEMENTS += _batch(
    "personal", "{suffix} общения", "Выполнить {n} личных задач",
    "charisma", lambda db: _count_tasks_done(db, "personal")
)
ACHIEVEMENTS += _batch(
    "debts_returned", "{suffix} доверия", "Получить назад {n} долгов",
    "charisma", lambda db: _count_paid_debts(db, "owed"),
    [(1, "Первый возврат", 30, 20), (3, "Три возврата", 60, 40),
     (5, "Пять возвратов", 100, 65), (10, "Десять возвратов", 200, 130)]
)
ACHIEVEMENTS += [
    {"code": "charisma_lv5", "title": "Обаятельный", "description": "Харизма достигла 5 уровня",
     "icon": "😊", "stat_key": "charisma", "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "charisma") >= 5},
    {"code": "charisma_lv10", "title": "Дипломат", "description": "Харизма достигла 10 уровня",
     "icon": "😊", "stat_key": "charisma", "xp_reward": 250, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "charisma") >= 10},
    {"code": "charisma_lv25", "title": "Лидер", "description": "Харизма достигла 25 уровня",
     "icon": "😊", "stat_key": "charisma", "xp_reward": 500, "stat_xp": 0,
     "check": lambda db: _stat_level(db, "charisma") >= 25},
    {"code": "charisma_combo", "title": "Социальная бабочка", "description": "10 личных задач + 3 возврата долга",
     "icon": "🦋", "stat_key": "charisma", "xp_reward": 120, "stat_xp": 75,
     "check": lambda db: _count_tasks_done(db, "personal") >= 10 and _count_paid_debts(db, "owed") >= 3},
    {"code": "charisma_popular", "title": "Популярный", "description": "Выполнить 100 личных задач",
     "icon": "🌟", "stat_key": "charisma", "xp_reward": 300, "stat_xp": 195,
     "check": lambda db: _count_tasks_done(db, "personal") >= 100},
]

# ──── ОБЩИЕ / МЕТА (general) ──── ~15
ACHIEVEMENTS += _batch(
    "total_tasks", "{suffix} дел", "Выполнить {n} задач суммарно",
    None, lambda db: _count_tasks_done(db),
    [(1, "Первое дело", 15, 0), (5, "Пять дел", 30, 0), (10, "Десять дел", 50, 0),
     (25, "Двадцать пять", 80, 0), (50, "Полсотни", 120, 0),
     (100, "Сотня", 200, 0), (200, "Две сотни", 300, 0),
     (500, "Пятьсот", 500, 0), (1000, "Тысяча", 800, 0)]
)
ACHIEVEMENTS += [
    {"code": "player_lv5", "title": "Подающий надежды", "description": "Достичь 5 уровня",
     "icon": "⭐", "stat_key": None, "xp_reward": 100, "stat_xp": 0,
     "check": lambda db: _player_level(db) >= 5},
    {"code": "player_lv10", "title": "Опытный", "description": "Достичь 10 уровня",
     "icon": "⭐", "stat_key": None, "xp_reward": 200, "stat_xp": 0,
     "check": lambda db: _player_level(db) >= 10},
    {"code": "player_lv25", "title": "Ветеран", "description": "Достичь 25 уровня",
     "icon": "⭐", "stat_key": None, "xp_reward": 500, "stat_xp": 0,
     "check": lambda db: _player_level(db) >= 25},
    {"code": "player_lv50", "title": "Легенда", "description": "Достичь 50 уровня",
     "icon": "👑", "stat_key": None, "xp_reward": 1000, "stat_xp": 0,
     "check": lambda db: _player_level(db) >= 50},
    {"code": "all_stats_5", "title": "Универсал", "description": "Все 6 характеристик на 5+ уровне",
     "icon": "🎯", "stat_key": None, "xp_reward": 300, "stat_xp": 0,
     "check": lambda db: all(_stat_level(db, k) >= 5 for k in
                             ["strength", "health", "intelligence", "discipline", "wisdom", "charisma"])},
    {"code": "all_stats_10", "title": "Совершенство", "description": "Все 6 характеристик на 10+ уровне",
     "icon": "💎", "stat_key": None, "xp_reward": 800, "stat_xp": 0,
     "check": lambda db: all(_stat_level(db, k) >= 10 for k in
                             ["strength", "health", "intelligence", "discipline", "wisdom", "charisma"])},
]


# ════════════════════════════════════════
#  ПУБЛИЧНЫЕ ФУНКЦИИ
# ════════════════════════════════════════

def get_all_achievement_defs() -> list[dict]:
    """Возвращает все определения достижений (без check-функций)"""
    return [
        {k: v for k, v in a.items() if k != "check"}
        for a in ACHIEVEMENTS
    ]


def check_all_achievements(db: Session, already_unlocked: set[str]) -> list[dict]:
    """Проверяет все достижения и возвращает список новых для разблокировки."""
    new_unlocks = []
    for ach in ACHIEVEMENTS:
        if ach["code"] in already_unlocked:
            continue
        try:
            if ach["check"](db):
                new_unlocks.append({k: v for k, v in ach.items() if k != "check"})
        except Exception:
            continue
    return new_unlocks
