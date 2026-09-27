from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models.exercise import Exercise
from app.models.settings import UserSettings
from app.services import stats as stats_service
from app.validation import ApiError

bp = Blueprint("stats", __name__, url_prefix="/api")


@bp.get("/exercises/<int:exercise_id>/stats")
def exercise_stats(exercise_id):
    exercise = db.session.get(Exercise, exercise_id)
    if exercise is None:
        raise ApiError("Exercise not found", 404)

    settings = UserSettings.get()
    metric = request.args.get("metric") or stats_service.default_metric_for(exercise)
    range_key = request.args.get("range", "all")

    series = stats_service.get_exercise_series(
        exercise, metric, range_key, settings.weight_unit, settings.distance_unit
    )
    prs = stats_service.get_exercise_prs(exercise, settings.weight_unit, settings.distance_unit)

    return jsonify(
        {
            "exercise_id": exercise.id,
            "metric": metric,
            "series": series,
            "personal_records": prs,
        }
    )


@bp.get("/stats/dashboard")
def dashboard():
    settings = UserSettings.get()
    return jsonify(stats_service.get_dashboard(settings.weight_unit, settings.distance_unit))


@bp.get("/stats/bodyweight")
def bodyweight_stats():
    settings = UserSettings.get()
    range_key = request.args.get("range", "all")
    return jsonify(stats_service.get_bodyweight_series(range_key, settings.weight_unit))
