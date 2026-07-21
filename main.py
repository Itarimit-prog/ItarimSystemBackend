import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from routers import tasks, templates, kanban, habits, workouts, finances, profile
from database import engine, init_db, get_db, SessionLocal, DATABASE_URL
from auth import verify_api_key
import db, kanban_db, habits_db, workouts_db, finance_db, profile_db
import logging

from models import TaskModel, TemplateModel
from kanban_models import BoardModel, KanbanColumnModel, KanbanCardModel
from habits_models import HabitModel, CheckModel, RelapseModel
from workouts_models import WorkoutModel, ExerciseModel, UserProfileModel
from finance_models import TransactionModel, DebtModel
from profile_models import PlayerModel, StatModel, UnlockedAchievementModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализируем БД (создаем таблицы) асинхронно
    await init_db()
    
    yield


app = FastAPI(title="Itarim System API", version="0.1.0", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
allow_origins = ["*"] if ALLOWED_ORIGINS == "*" else [
    o.strip() for o in ALLOWED_ORIGINS.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,  # Не совместимо с allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

_auth = [Depends(verify_api_key)]
app.include_router(tasks.router, dependencies=_auth)
app.include_router(templates.router, dependencies=_auth)
app.include_router(kanban.router, dependencies=_auth)
app.include_router(habits.router, dependencies=_auth)
app.include_router(workouts.router, dependencies=_auth)
app.include_router(finances.router, dependencies=_auth)
app.include_router(profile.router, dependencies=_auth)


@app.post("/reset-all", dependencies=_auth)
def reset_all(session: Session = Depends(get_db)):
    """
    Полный сброс приложения до заводских настроек: удаляет ВСЕ пользовательские
    данные во всех модулях (задачи, шаблоны, канбан, привычки, тренировки,
    финансы, профиль/XP/достижения). Каталог определений достижений не трогаем —
    он пересоздастся init_player() при следующем обращении к профилю.
    """
    for model in (
        TaskModel, TemplateModel,
        KanbanCardModel, KanbanColumnModel, BoardModel,
        CheckModel, RelapseModel, HabitModel,
        WorkoutModel, ExerciseModel, UserProfileModel,
        TransactionModel, DebtModel,
        UnlockedAchievementModel, StatModel, PlayerModel,
    ):
        session.query(model).delete()
    session.commit()
    return {"status": "ok"}


@app.get("/health")
def health():
    """
    Health check endpoint с проверкой подключения к БД.
    Возвращает статус приложения и базы данных.
    """
    health_data = {
        "status": "ok",
        "version": "0.1.0",
        "database": {
            "status": "unknown",
            "type": "postgresql" if DATABASE_URL.startswith("postgresql") else "sqlite"
        }
    }
    
    try:
        db_session = SessionLocal()
        try:
            db_session.execute(text("SELECT 1"))
            health_data["database"]["status"] = "connected"
        except Exception as e:
            logging.getLogger(__name__).error("Health check DB query failed: %s", e)
            health_data["database"]["status"] = "error"
            health_data["status"] = "degraded"
        finally:
            db_session.close()
    except Exception as e:
        logging.getLogger(__name__).error("Health check DB connection failed: %s", e)
        health_data["database"]["status"] = "error"
        health_data["status"] = "error"

    return health_data
