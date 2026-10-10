from datetime import date

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.bodyweight import BodyweightEntry
from app.models.constants import DISTANCE_UNITS, EXPERIENCE_LEVELS, PROGRESSION_METHODS, THEMES, WEIGHT_UNITS
from app.models.settings import UserSettings
from app.serializers import serialize_bodyweight_entry, serialize_settings
from app.services.sets_plan import rep_range_or_none
from app.validation import ApiError, require

bp = Blueprint("settings", __name__, url_prefix="/api")


@bp.get("/settings")
def get_settings():
    return jsonify(serialize_settings(UserSettings.get()))


@bp.patch("/settings")
def update_settings():
    settings = UserSettings.get()
    body = request.get_json(force=True) or {}

    if "weight_unit" in body:
        if body["weight_unit"] not in WEIGHT_UNITS:
            raise ApiError(f"weight_unit must be one of {WEIGHT_UNITS}")
        settings.weight_unit = body["weight_unit"]
    if "distance_unit" in body:
        if body["distance_unit"] not in DISTANCE_UNITS:
            raise ApiError(f"distance_unit must be one of {DISTANCE_UNITS}")
        settings.distance_unit = body["distance_unit"]
    if "default_rest_seconds" in body:
        settings.default_rest_seconds = body["default_rest_seconds"]
    if "theme" in body:
        if body["theme"] not in THEMES:
            raise ApiError(f"theme must be one of {THEMES}")
        settings.theme = body["theme"]
    if "progression_method" in body:
        if body["progression_method"] not in PROGRESSION_METHODS:
            raise ApiError(f"progression_method must be one of {PROGRESSION_METHODS}")
        settings.progression_method = body["progression_method"]
    if "experience" in body:
        if body["experience"] not in EXPERIENCE_LEVELS:
            raise ApiError(f"experience must be one of {EXPERIENCE_LEVELS}")
        settings.experience = body["experience"]
    if "default_rep_range" in body:
        text = str(body["default_rep_range"] or "").strip()
        if rep_range_or_none(text) is None:
            raise ApiError("default_rep_range must look like 8-12 (low end first, at least 1)")
        settings.default_rep_range = text
    for key in ("load_step_lb", "load_step_kg"):
        if key in body:
            value = body[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value <= 100:
                raise ApiError(f"{key} must be a number above 0 and up to 100")
            setattr(settings, key, float(value))

    db.session.commit()
    return jsonify(serialize_settings(settings))


@bp.get("/bodyweight")
def list_bodyweight():
    query = BodyweightEntry.query
    start = request.args.get("start")
    end = request.args.get("end")
    if start:
        query = query.filter(BodyweightEntry.recorded_at >= date.fromisoformat(start))
    if end:
        query = query.filter(BodyweightEntry.recorded_at <= date.fromisoformat(end))
    entries = query.order_by(BodyweightEntry.recorded_at.desc()).all()
    return jsonify([serialize_bodyweight_entry(e) for e in entries])


@bp.post("/bodyweight")
def upsert_bodyweight():
    body = request.get_json(force=True) or {}
    require(body, "weight")

    raw_date = body.get("recorded_at")
    recorded_at = date.fromisoformat(raw_date) if raw_date else date.today()
    settings = UserSettings.get()
    unit = body.get("unit", settings.weight_unit)

    entry = BodyweightEntry.query.filter_by(recorded_at=recorded_at).first()
    if entry is None:
        entry = BodyweightEntry(recorded_at=recorded_at, weight=body["weight"], unit=unit)
        db.session.add(entry)
    else:
        entry.weight = body["weight"]
        entry.unit = unit

    db.session.commit()
    return jsonify(serialize_bodyweight_entry(entry)), 201


@bp.delete("/bodyweight/<int:entry_id>")
def delete_bodyweight(entry_id):
    entry = db.session.get(BodyweightEntry, entry_id)
    if entry is None:
        raise ApiError("Entry not found", 404)
    db.session.delete(entry)
    db.session.commit()
    return "", 204
