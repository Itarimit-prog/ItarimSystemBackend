from sqlalchemy.orm import Session
from workouts_models import (
    WorkoutModel, Workout, WorkoutCreate, WorkoutUpdate,
    ExerciseModel, Exercise, ExerciseCreate,
    UserProfile, UserProfileUpdate
)
import json


# Пользовательский профиль (храним в отдельной таблице с одной записью)
# Seed data function removed to avoid test data in production
def _placeholder_seed_workouts(): pass


# ── CRUD тренировок ──

def get_all_workouts(db: Session) -> list[Workout]:
    workouts = db.query(WorkoutModel).order_by(WorkoutModel.date.desc()).all()
    result = []
    for w in workouts:
        exercises = json.loads(w.exercises) if w.exercises else []
        result.append(Workout(
            id=w.id,
            date=w.date,
            duration_minutes=w.duration_minutes,
            exercises=exercises,
            notes=w.notes
        ))
    return result


def get_workout(db: Session, workout_id: str) -> Workout | None:
    w = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id).first()
    if not w:
        return None
    
    exercises = json.loads(w.exercises) if w.exercises else []
    return Workout(
        id=w.id,
        date=w.date,
        duration_minutes=w.duration_minutes,
        exercises=exercises,
        notes=w.notes
    )


def create_workout(db: Session, workout: Workout) -> Workout:
    db_workout = WorkoutModel(
        id=workout.id,
        date=workout.date,
        duration_minutes=workout.duration_minutes,
        exercises=json.dumps(workout.exercises),
        notes=workout.notes
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return workout


def update_workout(db: Session, workout_id: str, updates: dict) -> Workout | None:
    db_workout = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id).first()
    if not db_workout:
        return None
    
    for key, value in updates.items():
        if key == 'exercises' and value is not None:
            value = json.dumps(value)
        setattr(db_workout, key, value)
    
    db.commit()
    db.refresh(db_workout)
    
    exercises = json.loads(db_workout.exercises) if db_workout.exercises else []
    return Workout(
        id=db_workout.id,
        date=db_workout.date,
        duration_minutes=db_workout.duration_minutes,
        exercises=exercises,
        notes=db_workout.notes
    )


def delete_workout(db: Session, workout_id: str) -> bool:
    db_workout = db.query(WorkoutModel).filter(WorkoutModel.id == workout_id).first()
    if not db_workout:
        return False
    
    db.delete(db_workout)
    db.commit()
    return True


# ── CRUD упражнений ──

def get_all_exercises(db: Session) -> list[Exercise]:
    exercises = db.query(ExerciseModel).all()
    result = []
    for e in exercises:
        muscle_groups = json.loads(e.muscle_groups) if e.muscle_groups else []
        result.append(Exercise(
            id=e.id,
            name=e.name,
            description=e.description,
            exercise_type=e.exercise_type,
            muscle_groups=muscle_groups,
            max_weight=e.max_weight,
            max_reps=e.max_reps,
            sets=e.sets
        ))
    return result


def get_exercise(db: Session, exercise_id: str) -> Exercise | None:
    e = db.query(ExerciseModel).filter(ExerciseModel.id == exercise_id).first()
    if not e:
        return None
    
    muscle_groups = json.loads(e.muscle_groups) if e.muscle_groups else []
    return Exercise(
        id=e.id,
        name=e.name,
        description=e.description,
        exercise_type=e.exercise_type,
        muscle_groups=muscle_groups,
        max_weight=e.max_weight,
        max_reps=e.max_reps,
        sets=e.sets
    )


def create_exercise(db: Session, exercise: Exercise) -> Exercise:
    db_exercise = ExerciseModel(
        id=exercise.id,
        name=exercise.name,
        description=exercise.description,
        exercise_type=exercise.exercise_type,
        muscle_groups=json.dumps(exercise.muscle_groups),
        max_weight=exercise.max_weight,
        max_reps=exercise.max_reps,
        sets=exercise.sets
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return exercise


def update_exercise(db: Session, exercise_id: str, updates: dict) -> Exercise | None:
    db_exercise = db.query(ExerciseModel).filter(ExerciseModel.id == exercise_id).first()
    if not db_exercise:
        return None
    
    for key, value in updates.items():
        if key == 'muscle_groups' and value is not None:
            value = json.dumps(value)
        setattr(db_exercise, key, value)
    
    db.commit()
    db.refresh(db_exercise)
    
    muscle_groups = json.loads(db_exercise.muscle_groups) if db_exercise.muscle_groups else []
    return Exercise(
        id=db_exercise.id,
        name=db_exercise.name,
        description=db_exercise.description,
        exercise_type=db_exercise.exercise_type,
        muscle_groups=muscle_groups,
        max_weight=db_exercise.max_weight,
        max_reps=db_exercise.max_reps,
        sets=db_exercise.sets
    )


def delete_exercise(db: Session, exercise_id: str) -> bool:
    db_exercise = db.query(ExerciseModel).filter(ExerciseModel.id == exercise_id).first()
    if not db_exercise:
        return False
    
    db.delete(db_exercise)
    db.commit()
    return True


# ── Профиль пользователя ──
# Храним в простой таблице с одной записью

def get_user_profile(db: Session) -> UserProfile:
    # Импортируем здесь чтобы избежать circular imports
    from workouts_models import UserProfileModel
    
    profile = db.query(UserProfileModel).first()
    if not profile:
        # Создаем дефолтный профиль
        profile = UserProfileModel(height_cm=180.0, weight_kg=75.0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return UserProfile(
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg
    )


def update_user_profile(db: Session, updates: dict) -> UserProfile:
    from workouts_models import UserProfileModel
    
    profile = db.query(UserProfileModel).first()
    if not profile:
        profile = UserProfileModel(**updates)
        db.add(profile)
    else:
        for key, value in updates.items():
            if value is not None:
                setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    
    return UserProfile(
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg
    )
