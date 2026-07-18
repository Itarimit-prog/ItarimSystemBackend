from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from workouts_models import (
    Workout, WorkoutCreate, WorkoutUpdate,
    Exercise, ExerciseCreate,
    UserProfile, UserProfileUpdate
)
from database import get_db
import workouts_db
import profile_db
import uuid

router = APIRouter(prefix="/workouts", tags=["workouts"])


# ── Упражнения (должны быть ДО /{workout_id}, чтобы не конфликтовать) ──

@router.get("/exercises/", response_model=list[Exercise])
def get_exercises(db: Session = Depends(get_db)):
    return workouts_db.get_all_exercises(db)


@router.get("/exercises/{exercise_id}", response_model=Exercise)
def get_exercise(exercise_id: str, db: Session = Depends(get_db)):
    exercise = workouts_db.get_exercise(db, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    return exercise


@router.post("/exercises/", response_model=Exercise, status_code=201)
def create_exercise(payload: ExerciseCreate, db: Session = Depends(get_db)):
    exercise = Exercise(id=str(uuid.uuid4()), **payload.model_dump())
    return workouts_db.create_exercise(db, exercise)


@router.put("/exercises/{exercise_id}", response_model=Exercise)
def update_exercise(exercise_id: str, payload: ExerciseCreate, db: Session = Depends(get_db)):
    updated = workouts_db.update_exercise(db, exercise_id, payload.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Упражнение не найдено")
    return updated


@router.delete("/exercises/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: str, db: Session = Depends(get_db)):
    if not workouts_db.delete_exercise(db, exercise_id):
        raise HTTPException(status_code=404, detail="Упражнение не найдено")


# ── Профиль пользователя ──

@router.get("/profile/", response_model=UserProfile)
def get_profile(db: Session = Depends(get_db)):
    return workouts_db.get_user_profile(db)


@router.put("/profile/", response_model=UserProfile)
def update_profile(payload: UserProfileUpdate, db: Session = Depends(get_db)):
    return workouts_db.update_user_profile(db, payload.model_dump(exclude_none=True))


# ── Тренировки ──

@router.get("/", response_model=list[Workout])
def get_workouts(db: Session = Depends(get_db)):
    return workouts_db.get_all_workouts(db)


@router.get("/{workout_id}", response_model=Workout)
def get_workout(workout_id: str, db: Session = Depends(get_db)):
    workout = workouts_db.get_workout(db, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    return workout


@router.post("/", status_code=201)
def create_workout(payload: WorkoutCreate, db: Session = Depends(get_db)):
    workout = Workout(id=str(uuid.uuid4()), **payload.model_dump())
    created = workouts_db.create_workout(db, workout)

    result = created.model_dump()
    # Тренировка → +25 XP к силе
    xp_data = profile_db.award_xp(db, 25, "strength")
    result["xp_result"] = xp_data

    return result


@router.put("/{workout_id}", response_model=Workout)
def update_workout(workout_id: str, payload: WorkoutUpdate, db: Session = Depends(get_db)):
    updated = workouts_db.update_workout(db, workout_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    return updated


@router.delete("/{workout_id}", status_code=204)
def delete_workout(workout_id: str, db: Session = Depends(get_db)):
    if not workouts_db.delete_workout(db, workout_id):
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
