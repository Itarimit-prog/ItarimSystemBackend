from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os
import logging

# Настраиваем логгер
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Загружаем .env файл
load_dotenv()

# Получаем DATABASE_URL из окружения
# По умолчанию используем SQLite для локальной разработки
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./life_os.db")


def _create_engine(url: str):
    """Создает engine с учетом типа БД"""
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False}
        )
    else:
        # PostgreSQL (Supabase Transaction Pooler)
        return create_engine(
            url,
            pool_size=3,
            max_overflow=5,
            pool_timeout=30,
            pool_recycle=300,
            pool_pre_ping=True
        )


engine = _create_engine(DATABASE_URL)


def _check_connection(eng):
    """Проверяет, можно ли подключиться к БД"""
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Не удалось подключиться к БД: {e}")
        return False


# Если не удалось подключиться к Supabase — падаем на SQLite
if not DATABASE_URL.startswith("sqlite") and not _check_connection(engine):
    logger.warning("Supabase недоступен, переключаемся на SQLite")
    DATABASE_URL = "sqlite:///./life_os.db"
    engine = _create_engine(DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency для FastAPI - предоставляет сессию БД
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=1)

async def init_db():
    """
    Асинхронная инициализация БД — создает все таблицы и добавляет недостающие колонки.
    Запускает синхронные SQLAlchemy-операции в отдельном потоке, чтобы не блокировать event loop.
    """
    from models import TaskModel, TemplateModel
    from kanban_models import BoardModel, KanbanColumnModel, KanbanCardModel
    from habits_models import HabitModel, CheckModel, RelapseModel
    from workouts_models import WorkoutModel, ExerciseModel, UserProfileModel
    from finance_models import TransactionModel, DebtModel
    from profile_models import PlayerModel, StatModel, AchievementDefModel, UnlockedAchievementModel

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, Base.metadata.create_all, engine)
    await loop.run_in_executor(_executor, _add_missing_columns)
    db_info = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Таблицы созданы успешно ({db_info})")


def _sync_init_db():
    """Синхронная версия init_db для обратной совместимости."""
    from models import TaskModel, TemplateModel
    from kanban_models import BoardModel, KanbanColumnModel, KanbanCardModel
    from habits_models import HabitModel, CheckModel, RelapseModel
    from workouts_models import WorkoutModel, ExerciseModel, UserProfileModel
    from finance_models import TransactionModel, DebtModel
    from profile_models import PlayerModel, StatModel, AchievementDefModel, UnlockedAchievementModel

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    db_info = DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Таблицы созданы успешно ({db_info})")


def _add_missing_columns():
    """
    Добавляет отсутствующие колонки в существующие таблицы (zero-downtime migrations)
    """
    from sqlalchemy import inspect
    try:
        inspector = inspect(engine)
        dialect = engine.url.get_dialect().name
        # PostgreSQL требует кавычки для зарезервированных слов (например, columns)
        quote = lambda name: f'"{name}"' if dialect == 'postgresql' else name
        
        # columns table — is_completed_column
        if 'columns' in inspector.get_table_names():
            cols = inspector.get_columns('columns')
            col_names = [c['name'] for c in cols]
            if 'is_completed_column' not in col_names:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {quote('columns')} ADD COLUMN is_completed_column INTEGER DEFAULT 0"))
                logger.info("Добавлена колонка is_completed_column в таблицу columns")
        
        # cards table — task_id
        if 'cards' in inspector.get_table_names():
            cols = inspector.get_columns('cards')
            col_names = [c['name'] for c in cols]
            if 'task_id' not in col_names:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {quote('cards')} ADD COLUMN task_id VARCHAR(36)"))
                logger.info("Добавлена колонка task_id в таблицу cards")
        
        # cards table — completed
        if 'cards' in inspector.get_table_names():
            cols = inspector.get_columns('cards')
            col_names = [c['name'] for c in cols]
            if 'completed' not in col_names:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {quote('cards')} ADD COLUMN completed INTEGER DEFAULT 0"))
                logger.info("Добавлена колонка completed в таблицу cards")
        
        # cards table — completed_at
        if 'cards' in inspector.get_table_names():
            cols = inspector.get_columns('cards')
            col_names = [c['name'] for c in cols]
            if 'completed_at' not in col_names:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {quote('cards')} ADD COLUMN completed_at VARCHAR(50)"))
                logger.info("Добавлена колонка completed_at в таблицу cards")
            else:
                # Проверяем, достаточно ли широкая колонка (миграция VARCHAR(20) -> VARCHAR(50))
                completed_at_col = next((c for c in cols if c['name'] == 'completed_at'), None)
                if completed_at_col and completed_at_col.get('type'):
                    type_str = str(completed_at_col['type'])
                    if '20' in type_str and '50' not in type_str:
                        with engine.begin() as conn:
                            if dialect == 'postgresql':
                                conn.execute(text(f"ALTER TABLE {quote('cards')} ALTER COLUMN completed_at TYPE VARCHAR(50)"))
                            else:
                                conn.execute(text(f"ALTER TABLE {quote('cards')} ALTER COLUMN completed_at VARCHAR(50)"))
                        logger.info("Расширена колонка completed_at до VARCHAR(50)")
        
        # exercises table — max_reps
        if 'exercises' in inspector.get_table_names():
            cols = inspector.get_columns('exercises')
            col_names = [c['name'] for c in cols]
            if 'max_reps' not in col_names:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {quote('exercises')} ADD COLUMN max_reps INTEGER"))
                logger.info("Добавлена колонка max_reps в таблицу exercises")
                
    except Exception as e:
        logger.warning(f"Не удалось добавить недостающие колонки: {e}")
