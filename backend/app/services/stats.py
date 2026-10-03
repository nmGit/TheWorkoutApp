"""Analytics: per-exercise progress series, PRs, dashboard, streaks.

Everything here is computed on read from WorkoutSet rows rather than
stored/cached, per docs/data_model.rst "Business rules" — cheap at
single-user data volumes and avoids a PR cache to keep in sync.
"""
from datetime import date, timedelta

from app.extensions import db
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.dates import local_date, local_midnight_utc
from app.services.units import convert_weight, meters_to_unit

RANGE_DAYS = {"3m": 90, "6m": 182, "12m": 365, "all": None}


def _range_cutoff(range_key: str):
    days = RANGE_DAYS.get(range_key, None)
    if days is None:
        return None
    return date.today() - timedelta(days=days)


def _completed_sets_query(exercise_id: int):
    return (
        db.session.query(WorkoutSet, Workout)
        .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(WorkoutExercise.exercise_id == exercise_id)
        .filter(Workout.completed_at.isnot(None))
    )


def _session_date(workout: Workout) -> date:
    return local_date(workout.started_at)


def get_exercise_series(exercise, metric: str, range_key: str, weight_unit: str, distance_unit: str):
    """One point per workout session, chronological, for `metric`."""
    cutoff = _range_cutoff(range_key)
    rows = _completed_sets_query(exercise.id).all()

    by_workout: dict[int, dict] = {}
    for s, w in rows:
        if cutoff and _session_date(w) < cutoff:
            continue
        entry = by_workout.setdefault(w.id, {"workout": w, "sets": []})
        entry["sets"].append(s)

    series = []
    for workout_id, data in by_workout.items():
        value = _aggregate_metric(data["sets"], metric, weight_unit, distance_unit)
        if value is None:
            continue
        series.append(
            {
                "date": _session_date(data["workout"]).isoformat(),
                "value": round(value, 2),
                "workout_id": workout_id,
            }
        )
    series.sort(key=lambda p: p["date"])
    return series


def _aggregate_metric(sets: list[WorkoutSet], metric: str, weight_unit: str, distance_unit: str):
    working_sets = [s for s in sets if not s.is_warmup]
    if not working_sets:
        return None

    if metric == "max_weight":
        values = [
            convert_weight(float(s.weight), s.weight_unit, weight_unit)
            for s in working_sets
            if s.weight is not None
        ]
        return max(values) if values else None

    if metric == "est_1rm":
        values = []
        for s in working_sets:
            raw = s.estimated_one_rm()
            if raw is None:
                continue
            values.append(convert_weight(raw, s.weight_unit, weight_unit))
        return max(values) if values else None

    if metric == "volume":
        total = 0.0
        found = False
        for s in working_sets:
            v = s.volume()
            if v is None:
                continue
            found = True
            total += convert_weight(v, s.weight_unit, weight_unit)
        return total if found else None

    if metric == "distance":
        values = [
            meters_to_unit(float(s.distance_meters), distance_unit)
            for s in working_sets
            if s.distance_meters is not None
        ]
        return max(values) if values else None

    if metric == "pace":
        # seconds per distance_unit; lower is faster, so we return the fastest
        best = None
        for s in working_sets:
            if not s.duration_seconds or not s.distance_meters:
                continue
            dist = meters_to_unit(float(s.distance_meters), distance_unit)
            if dist <= 0:
                continue
            pace = s.duration_seconds / dist
            if best is None or pace < best:
                best = pace
        return best

    raise ValueError(f"Unknown metric {metric}")


def default_metric_for(exercise) -> str:
    if exercise.tracking_type == "cardio":
        return "distance"
    if exercise.tracking_type in ("weight_reps",):
        return "est_1rm"
    return "volume"


def get_exercise_prs(exercise, weight_unit: str, distance_unit: str):
    rows = _completed_sets_query(exercise.id).all()
    if exercise.tracking_type == "cardio":
        return _cardio_prs(rows, distance_unit)
    return _strength_prs(rows, weight_unit)


def _strength_prs(rows, weight_unit: str):
    best_weight = None
    best_1rm = None
    best_volume = None

    for s, w in rows:
        if s.is_warmup:
            continue
        session_date = _session_date(w)

        if s.weight is not None:
            weight = convert_weight(float(s.weight), s.weight_unit, weight_unit)
            if best_weight is None or weight > best_weight["value"]:
                best_weight = {"value": weight, "date": session_date, "workout_id": w.id}

        est = s.estimated_one_rm()
        if est is not None:
            est = convert_weight(est, s.weight_unit, weight_unit)
            if best_1rm is None or est > best_1rm["value"]:
                best_1rm = {"value": est, "date": session_date, "workout_id": w.id}

        vol = s.volume()
        if vol is not None:
            vol = convert_weight(vol, s.weight_unit, weight_unit)
            if best_volume is None or vol > best_volume["value"]:
                best_volume = {"value": vol, "date": session_date, "workout_id": w.id}

    return {
        "max_weight": _round_pr(best_weight),
        "est_1rm": _round_pr(best_1rm),
        "best_set_volume": _round_pr(best_volume),
    }


def _cardio_prs(rows, distance_unit: str):
    longest = None
    fastest = None

    for s, w in rows:
        session_date = _session_date(w)
        if s.distance_meters is not None:
            dist = meters_to_unit(float(s.distance_meters), distance_unit)
            if longest is None or dist > longest["value"]:
                longest = {"value": dist, "date": session_date, "workout_id": w.id}
        if s.duration_seconds and s.distance_meters:
            dist = meters_to_unit(float(s.distance_meters), distance_unit)
            if dist > 0:
                pace = s.duration_seconds / dist
                if fastest is None or pace < fastest["value"]:
                    fastest = {"value": pace, "date": session_date, "workout_id": w.id}

    return {
        "longest_distance": _round_pr(longest),
        "fastest_pace": _round_pr(fastest),
    }


def _round_pr(pr):
    if pr is None:
        return None
    return {
        "value": round(pr["value"], 2),
        "date": pr["date"].isoformat(),
        "workout_id": pr["workout_id"],
    }


def compute_streak_weeks(workout_dates: set[date]) -> int:
    if not workout_dates:
        return 0
    weeks_with = {d.isocalendar()[:2] for d in workout_dates}

    today = date.today()
    streak = 1 if today.isocalendar()[:2] in weeks_with else 0

    cursor = today
    while True:
        cursor = cursor - timedelta(days=7)
        if cursor.isocalendar()[:2] in weeks_with:
            streak += 1
        else:
            break
    return streak


def get_dashboard(weight_unit: str, distance_unit: str):
    active = Workout.query.filter(Workout.completed_at.is_(None)).first()

    completed_dates = {
        local_date(w.started_at)
        for w in Workout.query.filter(Workout.completed_at.isnot(None)).all()
    }
    streak = compute_streak_weeks(completed_dates)

    recent_prs = _recent_prs(weight_unit, distance_unit)

    return {
        "active_workout_id": active.id if active else None,
        "current_streak_weeks": streak,
        "recent_prs": recent_prs,
    }


def _recent_prs(weight_unit: str, distance_unit: str, days: int = 7):
    from app.models.exercise_template import ExerciseTemplate

    cutoff = date.today() - timedelta(days=days)
    cutoff_dt = local_midnight_utc(cutoff)
    results = []

    exercise_ids = (
        db.session.query(WorkoutExercise.exercise_id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(Workout.completed_at.isnot(None))
        .filter(Workout.started_at >= cutoff_dt)
        .distinct()
        .all()
    )

    for (exercise_id,) in exercise_ids:
        exercise = db.session.get(ExerciseTemplate, exercise_id)
        if exercise is None:
            continue
        prs = get_exercise_prs(exercise, weight_unit, distance_unit)
        for metric, pr in prs.items():
            if pr and pr["date"] >= cutoff.isoformat():
                results.append(
                    {
                        "exercise_id": exercise.id,
                        "exercise_name": exercise.name,
                        "metric": metric,
                        **pr,
                    }
                )
    results.sort(key=lambda r: r["date"], reverse=True)
    return results


def get_bodyweight_series(range_key: str, unit: str):
    from app.models.bodyweight import BodyweightEntry

    cutoff = _range_cutoff(range_key)
    query = BodyweightEntry.query
    if cutoff:
        query = query.filter(BodyweightEntry.recorded_at >= cutoff)
    entries = query.order_by(BodyweightEntry.recorded_at.asc()).all()
    return [
        {
            "date": e.recorded_at.isoformat(),
            "weight": round(convert_weight(float(e.weight), e.unit, unit), 2),
        }
        for e in entries
    ]
