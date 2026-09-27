from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.exercise import EQUIPMENT_TYPES, TRACKING_TYPES, Exercise, MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.serializers import serialize_exercise, serialize_muscle_group
from app.services.exercise_templates import (
    equipment_type_for,
    muscle_group_name_for_body_part,
)
from app.validation import ApiError

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

    template = None
    template_id = body.get("template_id")
    if template_id is not None:
        template = db.session.get(ExerciseTemplate, template_id)
        if template is None:
            raise ApiError("Unknown template_id", 404)

    name = body.get("name") or (template.name if template else None)
    if not name:
        raise ApiError("Missing required field(s): name")

    muscle_group_id = body.get("muscle_group_id")
    if muscle_group_id is None and template is not None:
        mg_name = muscle_group_name_for_body_part(template.body_part)
        mg = MuscleGroup.query.filter_by(name=mg_name).first() if mg_name else None
        muscle_group_id = mg.id if mg else None
    if muscle_group_id is None:
        raise ApiError("Missing required field(s): muscle_group_id")
    group = db.session.get(MuscleGroup, muscle_group_id)
    if group is None:
        raise ApiError("Unknown muscle_group_id", 404)

    equipment = body.get("equipment")
    if equipment is None:
        equipment = equipment_type_for(template.equipment) if template else "other"
    if equipment not in EQUIPMENT_TYPES:
        raise ApiError(f"equipment must be one of {EQUIPMENT_TYPES}")

    tracking_type = body.get("tracking_type")
    if tracking_type is None:
        if template is not None and template.body_part == "cardio":
            tracking_type = "cardio"
        elif equipment == "bodyweight":
            tracking_type = "bodyweight_reps"
        else:
            tracking_type = "weight_reps"
    if tracking_type not in TRACKING_TYPES:
        raise ApiError(f"tracking_type must be one of {TRACKING_TYPES}")

    if template is None:
        # Every exercise is backed by a template: custom, from-scratch
        # exercises get one auto-created here so they show up as reusable
        # templates too, alongside the ones sourced from the dataset.
        template = ExerciseTemplate(
            name=name,
            category=group.name,
            equipment=equipment,
            is_custom=True,
        )
        db.session.add(template)
        db.session.flush()

    exercise = Exercise(
        name=name,
        muscle_group_id=muscle_group_id,
        equipment=equipment,
        tracking_type=tracking_type,
        is_custom=template.is_custom,
        default_rest_seconds=body.get("default_rest_seconds"),
        notes=body.get("notes"),
        template_id=template.id,
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
