from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from contextlib import asynccontextmanager
from routers import tasks, templates, kanban, habits, workouts, finances, profile
from database import engine, init_db, SessionLocal, DATABASE_URL
import db, kanban_db, habits_db, workouts_db, finance_db, profile_db
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализируем БД (создаем таблицы) асинхронно
    await init_db()
    
    yield


app = FastAPI(title="Itarim System API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Не совместимо с allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(templates.router)
app.include_router(kanban.router)
app.include_router(habits.router)
app.include_router(workouts.router)
app.include_router(finances.router)
app.include_router(profile.router)


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
            health_data["database"]["status"] = "error"
            health_data["database"]["error"] = str(e)
            health_data["status"] = "degraded"
        finally:
            db_session.close()
    except Exception as e:
        health_data["database"]["status"] = "error"
        health_data["database"]["error"] = str(e)
        health_data["status"] = "error"
    
    return health_data
