import re
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.exercise import Exercise
from app.models.settings import UserSettings
from app.models.template import WorkoutTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.serializers import serialize_set, serialize_workout
from app.validation import ApiError

bp = Blueprint("workouts", __name__, url_prefix="/api")


def _utcnow():
    return datetime.now(timezone.utc)


@bp.get("/workouts")
def list_workouts():
    query = Workout.query
    status = request.args.get("status")
    if status == "active":
        query = query.filter(Workout.completed_at.is_(None))
    elif status == "completed":
        query = query.filter(Workout.completed_at.isnot(None))
    template_id = request.args.get("template_id", type=int)
    if template_id:
        query = query.filter(Workout.template_id == template_id)

    start = request.args.get("start")
    end = request.args.get("end")
    if start:
        start_dt = datetime.combine(date.fromisoformat(start), datetime.min.time(), tzinfo=timezone.utc)
        query = query.filter(Workout.started_at >= start_dt)
    if end:
        end_dt = datetime.combine(date.fromisoformat(end), datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
        query = query.filter(Workout.started_at < end_dt)

    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    workouts = (
        query.order_by(Workout.started_at.desc()).offset(offset).limit(limit).all()
    )
    return jsonify([serialize_workout(w, include_exercises=False) for w in workouts])


@bp.get("/workouts/active")
def get_active_workout():
    workout = Workout.query.filter(Workout.completed_at.is_(None)).first()
    if workout is None:
        return "", 204
    return jsonify(serialize_workout(workout))


def _parse_target_reps(target_reps):
    """Pre-fill a set's rep count from a template target.

    ``target_reps`` is free-form (e.g. "8" or a range like "8-12") since
    it's just a display target, not a stored set value (see
    docs/data_model.rst). For a range, pre-fill with the low end -- some
    number beats leaving the field blank, and low-end-of-range is the
    conservative starting point for the first time through a set.
    """
    if target_reps is None:
        return None
    match = re.search(r"\d+", str(target_reps))
    return int(match.group()) if match else None


@bp.post("/workouts")
def start_workout():
    existing = Workout.query.filter(Workout.completed_at.is_(None)).first()
    if existing is not None:
        raise ApiError("A workout is already active", 409)

    body = request.get_json(silent=True) or {}
    template_id = body.get("template_id")
    settings = UserSettings.get()

    if template_id is not None:
        template = db.session.get(WorkoutTemplate, template_id)
        if template is None:
            raise ApiError("Template not found", 404)
        workout = Workout(name=template.name, template_id=template.id)
        db.session.add(workout)
        db.session.flush()

        for te in template.exercises:
            we = WorkoutExercise(
                workout_id=workout.id, exercise_id=te.exercise_id, position=te.position
            )
            db.session.add(we)
            db.session.flush()
            for i in range(te.target_sets or 1):
                db.session.add(
                    WorkoutSet(
                        workout_exercise_id=we.id,
                        position=i,
                        weight=te.target_weight,
                        weight_unit=settings.weight_unit if te.target_weight is not None else None,
                        reps=_parse_target_reps(te.target_reps),
                        completed=False,
                    )
                )
    else:
        workout = Workout(name="Workout")
        db.session.add(workout)

    db.session.commit()
    return jsonify(serialize_workout(workout)), 201


@bp.get("/workouts/<int:workout_id>")
def get_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    return jsonify(serialize_workout(workout))


@bp.patch("/workouts/<int:workout_id>")
def update_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    body = request.get_json(force=True) or {}

    if "name" in body:
        workout.name = body["name"]
    if "notes" in body:
        workout.notes = body["notes"]
    if "body_weight" in body:
        workout.body_weight = body["body_weight"]
    if body.get("completed_at") == "now" or body.get("finish") is True:
        if workout.completed_at is None:
            workout.completed_at = _utcnow()
            for we in workout.exercises:
                incomplete = [s for s in we.sets if not s.completed]
                for s in incomplete:
                    db.session.delete(s)

    db.session.commit()
    return jsonify(serialize_workout(workout))


@bp.delete("/workouts/<int:workout_id>")
def delete_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    db.session.delete(workout)
    db.session.commit()
    return "", 204


@bp.post("/workouts/<int:workout_id>/exercises")
def add_workout_exercise(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    body = request.get_json(force=True) or {}
    exercise_id = body.get("exercise_id")
    if not exercise_id or db.session.get(Exercise, exercise_id) is None:
        raise ApiError("Unknown exercise_id", 404)

    next_position = len(workout.exercises)
    we = WorkoutExercise(workout_id=workout.id, exercise_id=exercise_id, position=next_position)
    db.session.add(we)
    db.session.commit()
    return jsonify(serialize_workout(workout)), 201


@bp.delete("/workouts/<int:workout_id>/exercises/<int:workout_exercise_id>")
def remove_workout_exercise(workout_id, workout_exercise_id):
    we = db.session.get(WorkoutExercise, workout_exercise_id)
    if we is None or we.workout_id != workout_id:
        raise ApiError("Workout exercise not found", 404)
    db.session.delete(we)
    db.session.commit()
    return "", 204


@bp.post("/workout-exercises/<int:workout_exercise_id>/sets")
def add_set(workout_exercise_id):
    we = db.session.get(WorkoutExercise, workout_exercise_id)
    if we is None:
        raise ApiError("Workout exercise not found", 404)
    body = request.get_json(silent=True) or {}

    previous = we.sets[-1] if we.sets else None
    new_set = WorkoutSet(
        workout_exercise_id=we.id,
        position=len(we.sets),
        weight=body.get("weight", previous.weight if previous else None),
        weight_unit=body.get(
            "weight_unit", previous.weight_unit if previous else UserSettings.get().weight_unit
        ),
        reps=body.get("reps", previous.reps if previous else None),
        duration_seconds=body.get(
            "duration_seconds", previous.duration_seconds if previous else None
        ),
        distance_meters=body.get(
            "distance_meters", previous.distance_meters if previous else None
        ),
        completed=body.get("completed", False),
    )
    db.session.add(new_set)
    db.session.commit()
    return jsonify(serialize_set(new_set)), 201


@bp.patch("/sets/<int:set_id>")
def update_set(set_id):
    s = db.session.get(WorkoutSet, set_id)
    if s is None:
        raise ApiError("Set not found", 404)
    body = request.get_json(force=True) or {}

    for field in (
        "weight",
        "weight_unit",
        "reps",
        "duration_seconds",
        "distance_meters",
        "is_warmup",
        "is_dropset",
        "rpe",
        "completed",
    ):
        if field in body:
            setattr(s, field, body[field])

    db.session.commit()
    return jsonify(serialize_set(s))


@bp.delete("/sets/<int:set_id>")
def delete_set(set_id):
    s = db.session.get(WorkoutSet, set_id)
    if s is None:
        raise ApiError("Set not found", 404)
    db.session.delete(s)
    db.session.commit()
    return "", 204
