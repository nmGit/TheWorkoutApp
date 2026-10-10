import os
import re

from flask import Blueprint, abort, current_app, jsonify, request, send_from_directory
from werkzeug.utils import safe_join

from app.extensions import db
from app.models.exercise import EQUIPMENT_TYPES, TRACKING_TYPES, MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.serializers import (
    canonical_muscle_slug,
    muscle_swatch,
    serialize_exercise_template,
    serialize_muscle_group,
    serialize_set,
)
from app.services.dates import local_date
from app.services.exercise_templates import GROUP_MUSCLES
from app.validation import ApiError

bp = Blueprint("exercise_templates", __name__, url_prefix="/api")

MAX_LIMIT = 100


@bp.get("/muscle-groups")
def list_muscle_groups():
    groups = MuscleGroup.query.order_by(MuscleGroup.display_order).all()
    return jsonify([serialize_muscle_group(g) for g in groups])


@bp.get("/muscles/recency")
def muscle_recency():
    """Days since each muscle was last worked (muscles never worked are left out), with the
    regions each one lights up on the body diagram. Days are in the server's local calendar."""
    from datetime import date

    from app.services.muscle_regions import regions_for
    from app.services.recency import last_trained_dates

    from app.services.recency import IN_NEED_DAYS

    today = date.today()
    return jsonify(
        {
            "in_need_days": IN_NEED_DAYS,
            "muscles": {
                slug: {
                    "last_trained": day.isoformat(),
                    "days_since": (today - day).days,
                    "regions": regions_for(slug),
                }
                for slug, day in last_trained_dates().items()
            },
        }
    )


@bp.get("/muscle-groups/<int:group_id>/muscles")
def list_group_muscles(group_id):
    """The muscles that make up this group (e.g. "Pectoralis Major" under Chest),
    sorted by name, limited to those the group's exercises actually train as primary
    muscles. The group's membership comes from GROUP_MUSCLES, not from the exercises
    alone, so a stray primary doesn't leak into the wrong group."""
    group = db.session.get(MuscleGroup, group_id)
    if group is None:
        raise ApiError("Unknown muscle group", 404)
    members = GROUP_MUSCLES.get(group.name, set())
    found = {}
    for t in ExerciseTemplate.query.filter_by(muscle_group_id=group_id):
        for raw in t.primary_muscles or []:
            slug = canonical_muscle_slug(raw)
            if slug in members:
                found.setdefault(slug, muscle_swatch(raw))
    return jsonify(
        sorted(
            ({"slug": slug, **swatch} for slug, swatch in found.items()),
            key=lambda m: m["name"],
        )
    )


def _template_ids_for_muscle(slug: str) -> list[int]:
    """Exercises that work this muscle, primary or secondary, through the muscle table."""
    from app.models.muscle import ExerciseMuscle, Muscle

    rows = (
        db.session.query(ExerciseMuscle.exercise_id)
        .join(Muscle, Muscle.id == ExerciseMuscle.muscle_id)
        .filter(Muscle.slug == slug)
        .all()
    )
    return [exercise_id for (exercise_id,) in rows]


def _last_performed(template: ExerciseTemplate):
    we = (
        WorkoutExercise.query.join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(WorkoutExercise.exercise_id == template.id)
        .filter(Workout.completed_at.isnot(None))
        .order_by(Workout.started_at.desc())
        .first()
    )
    if we is None:
        return None
    sets = [s for s in we.sets if not s.is_warmup]
    if not sets:
        return {"date": local_date(we.workout.started_at).isoformat(), "summary": we.notes or "Done"}
    top = sets[0]
    parts = []
    if top.weight is not None and top.reps is not None:
        rounded = round(float(top.weight), 1)
        parts.append(f"{top.reps} x {rounded:g}{top.weight_unit or ''}")
    elif top.reps is not None:
        parts.append(f"{top.reps} reps")
    elif top.duration_seconds is not None:
        parts.append(f"{top.duration_seconds}s")
    summary = ", ".join(parts) if parts else "Done"
    return {"date": local_date(we.workout.started_at).isoformat(), "summary": summary}


@bp.get("/exercise-templates")
def list_exercise_templates():
    query = ExerciseTemplate.query
    q = request.args.get("q")
    if q:
        query = query.filter(ExerciseTemplate.name.ilike(f"%{q}%"))
    body_part = request.args.get("body_part")
    if body_part:
        query = query.filter(ExerciseTemplate.body_part == body_part)
    muscle_group_id = request.args.get("muscle_group_id", type=int)
    if muscle_group_id:
        if db.session.get(MuscleGroup, muscle_group_id) is None:
            raise ApiError("Unknown muscle_group_id", 404)
        query = query.filter(ExerciseTemplate.muscle_group_id == muscle_group_id)
    muscle = request.args.get("muscle")
    if muscle:
        query = query.filter(ExerciseTemplate.id.in_(_template_ids_for_muscle(muscle)))
    equipment = request.args.get("equipment")
    if equipment:
        query = query.filter(ExerciseTemplate.equipment == equipment)
    tracking_type = request.args.get("tracking_type")
    if tracking_type:
        query = query.filter(ExerciseTemplate.tracking_type == tracking_type)
    is_custom = request.args.get("is_custom")
    if is_custom is not None:
        query = query.filter(ExerciseTemplate.is_custom == (is_custom.lower() == "true"))

    total = query.count()
    limit = min(request.args.get("limit", default=40, type=int), MAX_LIMIT)
    offset = request.args.get("offset", default=0, type=int)
    items = query.order_by(ExerciseTemplate.name).offset(offset).limit(limit).all()

    return jsonify(
        {
            "total": total,
            "items": [
                serialize_exercise_template(t, last_performed=_last_performed(t)) for t in items
            ],
        }
    )


@bp.get("/exercise-templates/facets")
def exercise_template_facets():
    body_parts = [
        row[0]
        for row in db.session.query(ExerciseTemplate.body_part)
        .filter(ExerciseTemplate.body_part.isnot(None))
        .distinct()
        .order_by(ExerciseTemplate.body_part)
        .all()
    ]
    equipment = [
        row[0]
        for row in db.session.query(ExerciseTemplate.equipment_raw)
        .filter(ExerciseTemplate.equipment_raw.isnot(None))
        .distinct()
        .order_by(ExerciseTemplate.equipment_raw)
        .all()
    ]
    return jsonify({"body_parts": body_parts, "equipment": equipment})


@bp.post("/exercise-templates")
def create_exercise_template():
    body = request.get_json(force=True) or {}
    name = body.get("name")
    if not name:
        raise ApiError("Missing required field(s): name")

    muscle_group_id = body.get("muscle_group_id")
    if muscle_group_id is None:
        raise ApiError("Missing required field(s): muscle_group_id")
    group = db.session.get(MuscleGroup, muscle_group_id)
    if group is None:
        raise ApiError("Unknown muscle_group_id", 404)

    equipment = body.get("equipment", "other")
    if equipment not in EQUIPMENT_TYPES:
        raise ApiError(f"equipment must be one of {EQUIPMENT_TYPES}")

    tracking_type = body.get("tracking_type")
    if tracking_type is None:
        tracking_type = "bodyweight_reps" if equipment == "bodyweight" else "weight_reps"
    if tracking_type not in TRACKING_TYPES:
        raise ApiError(f"tracking_type must be one of {TRACKING_TYPES}")

    template = ExerciseTemplate(
        name=name,
        muscle_group_id=muscle_group_id,
        equipment=equipment,
        tracking_type=tracking_type,
        notes=body.get("notes"),
        is_custom=True,
    )
    db.session.add(template)
    db.session.commit()
    return jsonify(serialize_exercise_template(template)), 201


@bp.get("/exercise-templates/<int:template_id>")
def get_exercise_template(template_id):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None:
        raise ApiError("Exercise template not found", 404)
    return jsonify(serialize_exercise_template(template, last_performed=_last_performed(template)))


@bp.patch("/exercise-templates/<int:template_id>")
def update_exercise_template(template_id):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None:
        raise ApiError("Exercise template not found", 404)
    body = request.get_json(force=True) or {}

    if "name" in body:
        template.name = body["name"]
    if "muscle_group_id" in body:
        if db.session.get(MuscleGroup, body["muscle_group_id"]) is None:
            raise ApiError("Unknown muscle_group_id", 404)
        template.muscle_group_id = body["muscle_group_id"]
    if "equipment" in body:
        if body["equipment"] not in EQUIPMENT_TYPES:
            raise ApiError(f"equipment must be one of {EQUIPMENT_TYPES}")
        template.equipment = body["equipment"]
    if "tracking_type" in body:
        if body["tracking_type"] not in TRACKING_TYPES:
            raise ApiError(f"tracking_type must be one of {TRACKING_TYPES}")
        template.tracking_type = body["tracking_type"]
    if "notes" in body:
        template.notes = body["notes"]

    db.session.commit()
    return jsonify(serialize_exercise_template(template))


@bp.delete("/exercise-templates/<int:template_id>")
def delete_exercise_template(template_id):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None:
        raise ApiError("Exercise template not found", 404)
    if not template.is_custom:
        raise ApiError("Cannot delete a dataset-sourced exercise", 409)
    if template.has_logged_sets():
        raise ApiError("Cannot delete an exercise with logged history", 409)
    db.session.delete(template)
    db.session.commit()
    return "", 204


IMAGE_CACHE_SECONDS = 24 * 60 * 60


def _serve_dataset_file(config_key, relative_path):
    """Serve a file out of one of the bundled dataset submodules, or None if
    it isn't there (path-traversal safe via safe_join)."""
    full_path = safe_join(current_app.config[config_key], relative_path)
    if full_path is None or not os.path.isfile(full_path):
        return None
    directory, filename = os.path.split(full_path)
    return send_from_directory(directory, filename, max_age=IMAGE_CACHE_SECONDS)


@bp.get("/exercise-templates/<int:template_id>/image", defaults={"n": 0})
@bp.get("/exercise-templates/<int:template_id>/image/<int:n>")
def get_exercise_template_image(template_id, n):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None:
        abort(404)

    # RepDB's poses (start/peak) win; the original dataset's single image is
    # the fallback for the first image when RepDB has none (or its file is
    # missing, e.g. the submodule isn't checked out).
    candidates = []
    if template.repdb_images and n < len(template.repdb_images):
        candidates.append(("REPDB_DATASET_DIR", template.repdb_images[n]))
    if n == 0 and template.image_path:
        candidates.append(("EXERCISE_DATASET_DIR", template.image_path))

    for config_key, relative_path in candidates:
        response = _serve_dataset_file(config_key, relative_path)
        if response is not None:
            return response
    abort(404)


@bp.get("/muscles/<slug>/image")
def get_muscle_image(slug):
    # RepDB ships a highlighted-body diagram per muscle, dash-named
    # (images/muscles/pectoralis-major.webp); we address muscles by their
    # underscore slug (pectoralis_major).
    if not re.fullmatch(r"[a-z0-9_]+", slug):
        abort(404)
    response = _serve_dataset_file(
        "REPDB_DATASET_DIR", f"images/muscles/{slug.replace('_', '-')}.webp"
    )
    if response is None:
        abort(404)
    return response


@bp.get("/exercise-templates/<int:template_id>/history")
def exercise_template_history(template_id):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None:
        raise ApiError("Exercise template not found", 404)

    limit = request.args.get("limit", default=20, type=int)
    offset = request.args.get("offset", default=0, type=int)

    query = (
        WorkoutExercise.query.join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(WorkoutExercise.exercise_id == template_id)
        .filter(Workout.completed_at.isnot(None))
        .order_by(Workout.started_at.desc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    items = [
        {
            "workout_id": we.workout_id,
            "date": local_date(we.workout.started_at).isoformat(),
            "notes": we.notes,
            "sets": [serialize_set(s) for s in we.sets],
        }
        for we in rows
    ]

    return jsonify({"total": total, "items": items})
