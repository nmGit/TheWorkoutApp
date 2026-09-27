from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.exercise import EQUIPMENT_TYPES, TRACKING_TYPES, Exercise, MuscleGroup
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.serializers import serialize_exercise, serialize_muscle_group
from app.validation import ApiError, require

bp = Blueprint("exercises", __name__, url_prefix="/api")


@bp.get("/muscle-groups")
def list_muscle_groups():
    groups = MuscleGroup.query.order_by(MuscleGroup.display_order).all()
    return jsonify([serialize_muscle_group(g) for g in groups])


def _last_performed(exercise: Exercise):
    we = (
        WorkoutExercise.query.join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(WorkoutExercise.exercise_id == exercise.id)
        .filter(Workout.completed_at.isnot(None))
        .order_by(Workout.started_at.desc())
        .first()
    )
    if we is None:
        return None
    sets = [s for s in we.sets if not s.is_warmup]
    if not sets:
        return {"date": we.workout.started_at.date().isoformat(), "summary": we.notes or "Done"}
    top = sets[0]
    parts = []
    if top.weight is not None and top.reps is not None:
        parts.append(f"{top.reps} x {float(top.weight):g}{top.weight_unit or ''}")
    elif top.reps is not None:
        parts.append(f"{top.reps} reps")
    elif top.duration_seconds is not None:
        parts.append(f"{top.duration_seconds}s")
    summary = ", ".join(parts) if parts else "Done"
    return {"date": we.workout.started_at.date().isoformat(), "summary": summary}


@bp.get("/exercises")
def list_exercises():
    query = Exercise.query
    q = request.args.get("q")
    if q:
        query = query.filter(Exercise.name.ilike(f"%{q}%"))
    muscle_group_id = request.args.get("muscle_group_id", type=int)
    if muscle_group_id:
        query = query.filter(Exercise.muscle_group_id == muscle_group_id)
    equipment = request.args.get("equipment")
    if equipment:
        query = query.filter(Exercise.equipment == equipment)

    exercises = query.order_by(Exercise.name).all()
    return jsonify(
        [serialize_exercise(e, last_performed=_last_performed(e)) for e in exercises]
    )


@bp.post("/exercises")
def create_exercise():
    body = request.get_json(force=True) or {}
    require(body, "name", "muscle_group_id", "tracking_type")

    if body["tracking_type"] not in TRACKING_TYPES:
        raise ApiError(f"tracking_type must be one of {TRACKING_TYPES}")
    equipment = body.get("equipment", "other")
    if equipment not in EQUIPMENT_TYPES:
        raise ApiError(f"equipment must be one of {EQUIPMENT_TYPES}")
    if db.session.get(MuscleGroup, body["muscle_group_id"]) is None:
        raise ApiError("Unknown muscle_group_id", 404)

    exercise = Exercise(
        name=body["name"],
        muscle_group_id=body["muscle_group_id"],
        equipment=equipment,
        tracking_type=body["tracking_type"],
        is_custom=True,
        default_rest_seconds=body.get("default_rest_seconds"),
        notes=body.get("notes"),
    )
    db.session.add(exercise)
    db.session.commit()
    return jsonify(serialize_exercise(exercise)), 201


@bp.get("/exercises/<int:exercise_id>")
def get_exercise(exercise_id):
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        raise ApiError("Exercise not found", 404)
    return jsonify(serialize_exercise(exercise, last_performed=_last_performed(exercise)))


@bp.patch("/exercises/<int:exercise_id>")
def update_exercise(exercise_id):
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        raise ApiError("Exercise not found", 404)
    body = request.get_json(force=True) or {}

    if "name" in body:
        exercise.name = body["name"]
    if "muscle_group_id" in body:
        if db.session.get(MuscleGroup, body["muscle_group_id"]) is None:
            raise ApiError("Unknown muscle_group_id", 404)
        exercise.muscle_group_id = body["muscle_group_id"]
    if "equipment" in body:
        if body["equipment"] not in EQUIPMENT_TYPES:
            raise ApiError(f"equipment must be one of {EQUIPMENT_TYPES}")
        exercise.equipment = body["equipment"]
    if "tracking_type" in body:
        if body["tracking_type"] not in TRACKING_TYPES:
            raise ApiError(f"tracking_type must be one of {TRACKING_TYPES}")
        exercise.tracking_type = body["tracking_type"]
    if "default_rest_seconds" in body:
        exercise.default_rest_seconds = body["default_rest_seconds"]
    if "notes" in body:
        exercise.notes = body["notes"]

    db.session.commit()
    return jsonify(serialize_exercise(exercise))


@bp.delete("/exercises/<int:exercise_id>")
def delete_exercise(exercise_id):
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        raise ApiError("Exercise not found", 404)
    if exercise.has_logged_sets():
        raise ApiError("Cannot delete an exercise with logged history", 409)
    db.session.delete(exercise)
    db.session.commit()
    return "", 204


@bp.get("/exercises/<int:exercise_id>/history")
def exercise_history(exercise_id):
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        raise ApiError("Exercise not found", 404)

    limit = request.args.get("limit", default=20, type=int)
    offset = request.args.get("offset", default=0, type=int)

    query = (
        WorkoutExercise.query.join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(WorkoutExercise.exercise_id == exercise_id)
        .filter(Workout.completed_at.isnot(None))
        .order_by(Workout.started_at.desc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    from app.serializers import serialize_set

    items = []
    for we in rows:
        items.append(
            {
                "workout_id": we.workout_id,
                "date": we.workout.started_at.date().isoformat(),
                "notes": we.notes,
                "sets": [serialize_set(s) for s in we.sets],
            }
        )

    return jsonify({"total": total, "items": items})
