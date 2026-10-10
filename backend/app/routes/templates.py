from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.template import TemplateExercise, WorkoutTemplate
from app.models.workout import Workout
from app.serializers import serialize_template
from app.validation import ApiError, require

bp = Blueprint("templates", __name__, url_prefix="/api")


@bp.get("/templates")
def list_templates():
    templates = WorkoutTemplate.query.order_by(WorkoutTemplate.display_order).all()
    return jsonify([serialize_template(t) for t in templates])


def _apply_exercises(template: WorkoutTemplate, exercises: list[dict]):
    for te in list(template.exercises):
        db.session.delete(te)
    for position, item in enumerate(exercises):
        if not item.get("exercise_id"):
            raise ApiError("Each template exercise requires exercise_id")
        if db.session.get(ExerciseTemplate, item["exercise_id"]) is None:
            raise ApiError(f"Unknown exercise_id {item['exercise_id']}", 404)
        db.session.add(
            TemplateExercise(
                template=template,
                exercise_id=item["exercise_id"],
                position=position,
                target_sets=item.get("target_sets"),
                warmup_sets=item.get("warmup_sets") or 0,
                drop_sets=item.get("drop_sets") or 0,
                target_reps=item.get("target_reps"),
                target_weight=item.get("target_weight"),
            )
        )


@bp.post("/templates")
def create_template():
    body = request.get_json(force=True) or {}
    require(body, "name")

    max_order = db.session.query(db.func.max(WorkoutTemplate.display_order)).scalar() or 0
    template = WorkoutTemplate(
        name=body["name"], notes=body.get("notes"), display_order=max_order + 1
    )
    db.session.add(template)
    db.session.flush()
    _apply_exercises(template, body.get("exercises", []))
    db.session.commit()
    return jsonify(serialize_template(template)), 201


@bp.post("/templates/from-workout/<int:workout_id>")
def create_template_from_workout(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)

    max_order = db.session.query(db.func.max(WorkoutTemplate.display_order)).scalar() or 0
    template = WorkoutTemplate(name=workout.name, display_order=max_order + 1)
    db.session.add(template)
    db.session.flush()

    for position, we in enumerate(workout.exercises):
        last_set = we.sets[-1] if we.sets else None
        db.session.add(
            TemplateExercise(
                template=template,
                exercise_id=we.exercise_id,
                position=position,
                target_sets=len(we.sets) or None,
                target_reps=str(last_set.reps) if last_set and last_set.reps else None,
                target_weight=last_set.weight if last_set else None,
            )
        )
    db.session.commit()
    return jsonify(serialize_template(template)), 201


@bp.get("/templates/<int:template_id>")
def get_template(template_id):
    template = db.session.get(WorkoutTemplate, template_id)
    if template is None:
        raise ApiError("Template not found", 404)
    return jsonify(serialize_template(template))


@bp.patch("/templates/<int:template_id>")
def update_template(template_id):
    template = db.session.get(WorkoutTemplate, template_id)
    if template is None:
        raise ApiError("Template not found", 404)
    body = request.get_json(force=True) or {}

    if "name" in body:
        template.name = body["name"]
    if "notes" in body:
        template.notes = body["notes"]
    if "exercises" in body:
        _apply_exercises(template, body["exercises"])

    db.session.commit()
    return jsonify(serialize_template(template))


@bp.patch("/templates/reorder")
def reorder_templates():
    body = request.get_json(force=True) or []
    for item in body:
        template = db.session.get(WorkoutTemplate, item["id"])
        if template is None:
            raise ApiError(f"Unknown template id {item['id']}", 404)
        template.display_order = item["display_order"]
    db.session.commit()
    return "", 204


@bp.delete("/templates/<int:template_id>")
def delete_template(template_id):
    template = db.session.get(WorkoutTemplate, template_id)
    if template is None:
        raise ApiError("Template not found", 404)
    db.session.delete(template)
    db.session.commit()
    return "", 204
