from sqlalchemy.orm import Session
from workouts_models import (
    WorkoutModel, Workout, WorkoutCreate, WorkoutUpdate,
    ExerciseModel, Exercise, ExerciseCreate,
    RoutineModel, Routine, RoutineCreate, RoutineUpdate,
    RoutineExerciseModel, RoutineExerciseOut, RoutineExerciseCreate, RoutineExerciseUpdate,
    UserProfile, UserProfileUpdate
)
import json
import uuid


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
            notes=w.notes,
            routine_id=w.routine_id
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
        notes=w.notes,
        routine_id=w.routine_id
    )


def create_workout(db: Session, workout: Workout) -> Workout:
    db_workout = WorkoutModel(
        id=workout.id,
        date=workout.date,
        duration_minutes=workout.duration_minutes,
        exercises=json.dumps(workout.exercises),
        notes=workout.notes,
        routine_id=workout.routine_id
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
        notes=db_workout.notes,
        routine_id=db_workout.routine_id
    )


def get_last_workout_date(db: Session, routine_id: str) -> str | None:
    w = db.query(WorkoutModel).filter(WorkoutModel.routine_id == routine_id).order_by(WorkoutModel.date.desc()).first()
    return w.date if w else None


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


# ── Тренировки (роутины) ──

def get_all_routines(db: Session) -> list[Routine]:
    routines = db.query(RoutineModel).order_by(RoutineModel.position).all()
    return [Routine(id=r.id, name=r.name, icon=r.icon, position=r.position) for r in routines]


def create_routine(db: Session, name: str, icon: str | None = None) -> Routine:
    position = db.query(RoutineModel).count()
    db_routine = RoutineModel(id=str(uuid.uuid4()), name=name, icon=icon, position=position)
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    return Routine(id=db_routine.id, name=db_routine.name, icon=db_routine.icon, position=db_routine.position)


def update_routine(db: Session, routine_id: str, updates: dict) -> Routine | None:
    db_routine = db.query(RoutineModel).filter(RoutineModel.id == routine_id).first()
    if not db_routine:
        return None
    for key, value in updates.items():
        if value is not None:
            setattr(db_routine, key, value)
    db.commit()
    db.refresh(db_routine)
    return Routine(id=db_routine.id, name=db_routine.name, icon=db_routine.icon, position=db_routine.position)


def delete_routine(db: Session, routine_id: str) -> bool:
    db_routine = db.query(RoutineModel).filter(RoutineModel.id == routine_id).first()
    if not db_routine:
        return False
    # Удаляем связанные упражнения-в-роутине и сами упражнения (они не переиспользуются между роутинами)
    links = db.query(RoutineExerciseModel).filter(RoutineExerciseModel.routine_id == routine_id).all()
    for link in links:
        ex = db.query(ExerciseModel).filter(ExerciseModel.id == link.exercise_id).first()
        if ex:
            db.delete(ex)
        db.delete(link)
    db.delete(db_routine)
    db.commit()
    return True


def _routine_exercise_out(db: Session, link: RoutineExerciseModel) -> RoutineExerciseOut | None:
    ex = db.query(ExerciseModel).filter(ExerciseModel.id == link.exercise_id).first()
    if not ex:
        return None
    muscle_groups = json.loads(ex.muscle_groups) if ex.muscle_groups else []
    return RoutineExerciseOut(
        id=link.id,
        exercise_id=ex.id,
        name=ex.name,
        description=ex.description,
        exercise_type=ex.exercise_type,
        muscle_groups=muscle_groups,
        sets=link.sets,
        reps=link.reps,
        weight=link.weight,
        position=link.position
    )


def get_routine_exercises(db: Session, routine_id: str) -> list[RoutineExerciseOut]:
    links = db.query(RoutineExerciseModel).filter(
        RoutineExerciseModel.routine_id == routine_id
    ).order_by(RoutineExerciseModel.position).all()
    result = []
    for link in links:
        out = _routine_exercise_out(db, link)
        if out:
            result.append(out)
    return result


def add_routine_exercise(db: Session, routine_id: str, payload: RoutineExerciseCreate) -> RoutineExerciseOut:
    db_exercise = ExerciseModel(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        exercise_type=payload.exercise_type,
        muscle_groups=json.dumps(payload.muscle_groups),
    )
    db.add(db_exercise)

    position = db.query(RoutineExerciseModel).filter(RoutineExerciseModel.routine_id == routine_id).count()
    db_link = RoutineExerciseModel(
        id=str(uuid.uuid4()),
        routine_id=routine_id,
        exercise_id=db_exercise.id,
        sets=payload.sets,
        reps=payload.reps,
        weight=payload.weight,
        position=position
    )
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return _routine_exercise_out(db, db_link)


def update_routine_exercise(db: Session, routine_exercise_id: str, updates: dict) -> RoutineExerciseOut | None:
    db_link = db.query(RoutineExerciseModel).filter(RoutineExerciseModel.id == routine_exercise_id).first()
    if not db_link:
        return None
    for key, value in updates.items():
        if value is not None:
            setattr(db_link, key, value)
    db.commit()
    db.refresh(db_link)
    return _routine_exercise_out(db, db_link)


def delete_routine_exercise(db: Session, routine_exercise_id: str) -> bool:
    db_link = db.query(RoutineExerciseModel).filter(RoutineExerciseModel.id == routine_exercise_id).first()
    if not db_link:
        return False
    ex = db.query(ExerciseModel).filter(ExerciseModel.id == db_link.exercise_id).first()
    if ex:
        db.delete(ex)
    db.delete(db_link)
    db.commit()
    return True


def ensure_default_routine(db: Session) -> None:
    """
    Разовая миграция: если роутинов ещё нет, но есть упражнения без привязки —
    собрать их все в одну тренировку "Основная".
    """
    if db.query(RoutineModel).count() > 0:
        return

    orphan_exercises = db.query(ExerciseModel).all()
    if not orphan_exercises:
        return

    routine = RoutineModel(id=str(uuid.uuid4()), name="Основная", icon="🏋️", position=0)
    db.add(routine)
    db.flush()

    for i, ex in enumerate(orphan_exercises):
        link = RoutineExerciseModel(
            id=str(uuid.uuid4()),
            routine_id=routine.id,
            exercise_id=ex.id,
            sets=ex.sets,
            reps=ex.max_reps,
            weight=ex.max_weight,
            position=i
        )
        db.add(link)

    db.commit()


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
