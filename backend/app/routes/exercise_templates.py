import os

from flask import Blueprint, abort, current_app, jsonify, request, send_from_directory
from werkzeug.utils import safe_join

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.serializers import serialize_exercise_template
from app.validation import ApiError

bp = Blueprint("exercise_templates", __name__, url_prefix="/api")

MAX_LIMIT = 100


@bp.get("/exercise-templates")
def list_exercise_templates():
    query = ExerciseTemplate.query
    q = request.args.get("q")
    if q:
        query = query.filter(ExerciseTemplate.name.ilike(f"%{q}%"))
    body_part = request.args.get("body_part")
    if body_part:
        query = query.filter(ExerciseTemplate.body_part == body_part)
    equipment = request.args.get("equipment")
    if equipment:
        query = query.filter(ExerciseTemplate.equipment == equipment)
    is_custom = request.args.get("is_custom")
    if is_custom is not None:
        query = query.filter(ExerciseTemplate.is_custom == (is_custom.lower() == "true"))

    total = query.count()
    limit = min(request.args.get("limit", default=40, type=int), MAX_LIMIT)
    offset = request.args.get("offset", default=0, type=int)
    items = query.order_by(ExerciseTemplate.name).offset(offset).limit(limit).all()

    return jsonify(
        {"total": total, "items": [serialize_exercise_template(t) for t in items]}
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
        for row in db.session.query(ExerciseTemplate.equipment)
        .filter(ExerciseTemplate.equipment.isnot(None))
        .distinct()
        .order_by(ExerciseTemplate.equipment)
        .all()
    ]
    return jsonify({"body_parts": body_parts, "equipment": equipment})


@bp.get("/exercise-templates/<int:template_id>")
def get_exercise_template(template_id):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None:
        raise ApiError("Exercise template not found", 404)
    return jsonify(serialize_exercise_template(template))


@bp.get("/exercise-templates/<int:template_id>/image")
def get_exercise_template_image(template_id):
    template = db.session.get(ExerciseTemplate, template_id)
    if template is None or not template.image_path:
        abort(404)

    dataset_dir = current_app.config["EXERCISE_DATASET_DIR"]
    full_path = safe_join(dataset_dir, template.image_path)
    if full_path is None or not os.path.isfile(full_path):
        abort(404)

    directory, filename = os.path.split(full_path)
    return send_from_directory(directory, filename)
