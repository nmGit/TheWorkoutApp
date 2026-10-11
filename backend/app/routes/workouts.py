import re
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.settings import UserSettings
from app.models.template import WorkoutTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.serializers import serialize_set, serialize_workout
from app.services.dates import local_midnight_utc
from app.services.sets_plan import SetPlanSpec, make_planned_sets, plan_sets
from app.services.generated_v2 import score_series_v2, strength_for_workout
from app.services.strength import completed_workouts
from app.services.supersets import (
    equalize_workout_superset_sets,
    link_pair,
    normalize_superset_groups,
    unlink,
)
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
        query = query.filter(Workout.started_at >= local_midnight_utc(date.fromisoformat(start)))
    if end:
        end_dt = local_midnight_utc(date.fromisoformat(end)) + timedelta(days=1)
        query = query.filter(Workout.started_at < end_dt)

    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    # The muscle summary on each card reads every exercise's template, so load those
    # in batches rather than one query per workout.
    workouts = (
        query.options(
            selectinload(Workout.exercises)
            .selectinload(WorkoutExercise.exercise)
            .selectinload(ExerciseTemplate.app_muscle_group)
        )
        .order_by(Workout.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return jsonify([serialize_workout(w, include_exercises=False) for w in workouts])


@bp.get("/workouts/<int:workout_id>/strength")
def get_workout_strength(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    return jsonify(strength_for_workout(workout))


@bp.get("/strength/history")
def get_strength_history():
    """The strength status of every completed workout, oldest first: the score (null during
    warm-up), each muscle's status, and the template it came from."""
    series = score_series_v2(completed_workouts())
    return jsonify(
        [
            {
                "workout_id": point["workout_id"],
                "date": point["started_at"].replace(tzinfo=timezone.utc).isoformat(),
                "template_id": point["template_id"],
                "score": point["score"],
                "muscles": point["muscles"],
            }
            for point in series
        ]
    )


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
            db.session.add_all(make_planned_sets(we.id, plan_sets(te)))
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


@bp.get("/workouts/generate/groups")
def generate_groups():
    """The training groups in order of need, for the generate panel."""
    from datetime import date

    from app.services.generate import group_ranking

    return jsonify(group_ranking(date.today()))


@bp.post("/workouts/generated")
def create_generated():
    """A workout built from the muscles that are most overdue (see services/generate.py)."""
    from datetime import date

    from app.services.generate import create_generated_workout, plan

    body = request.get_json(silent=True) or {}
    count = body.get("count", 4)
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
        raise ApiError("count must be a whole number from 1 to 10")
    if Workout.query.filter(Workout.completed_at.is_(None)).first() is not None:
        raise ApiError("A workout is already active", 409)
    familiar_first = body.get("familiar_first", True)
    groups = body.get("groups")
    if groups is not None and (not isinstance(groups, list) or not all(isinstance(g, str) for g in groups)):
        raise ApiError("groups must be a list of group names")
    chosen = plan(
        count,
        bool(body.get("stretching")),
        bool(body.get("cardio")),
        date.today(),
        familiar_first=bool(familiar_first),
        groups=groups,
    )
    if not chosen:
        raise ApiError("No exercises with history to build a workout from yet", 409)
    workout = create_generated_workout(chosen)
    return jsonify(serialize_workout(workout)), 201


@bp.post("/workouts/<int:workout_id>/exercises")
def add_workout_exercise(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    body = request.get_json(force=True) or {}
    exercise_id = body.get("exercise_id")
    if not exercise_id or db.session.get(ExerciseTemplate, exercise_id) is None:
        raise ApiError("Unknown exercise_id", 404)

    next_position = len(workout.exercises)
    we = WorkoutExercise(workout_id=workout.id, exercise_id=exercise_id, position=next_position)
    db.session.add(we)
    db.session.commit()
    return jsonify(serialize_workout(workout)), 201


@bp.patch("/workouts/<int:workout_id>/exercises/reorder")
def reorder_workout_exercises(workout_id):
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)

    body = request.get_json(silent=True)
    ids = body.get("exercise_ids") if isinstance(body, dict) else None
    if not isinstance(ids, list) or not all(
        isinstance(i, int) and not isinstance(i, bool) for i in ids
    ):
        raise ApiError("exercise_ids must be a list of ints", 400)
    if len(set(ids)) != len(ids):
        raise ApiError("exercise_ids contains duplicates", 400)

    by_id = {we.id: we for we in workout.exercises}
    if set(ids) != set(by_id.keys()):
        raise ApiError("exercise_ids must match this workout's exercises exactly", 400)

    for position, we_id in enumerate(ids):
        by_id[we_id].position = position

    # A reorder can split a superset apart (dissolving it) or, if it happens to land two members
    # back together, nothing more needs equalizing since they were already equal.
    equalize_workout_superset_sets(workout)
    db.session.commit()
    return jsonify(serialize_workout(workout))


@bp.patch("/workouts/<int:workout_id>/exercises/<int:workout_exercise_id>")
def update_workout_exercise(workout_id, workout_exercise_id):
    """Edits what's specific to this instance of the exercise: its notes, and un-pairing it from
    a superset. The template's notes (shared by every instance) are edited on the exercise.
    Pairing two exercises *into* a superset is POST .../exercises/link instead -- both sides need
    to change together in one transaction, which a single exercise's PATCH can't do."""
    we = db.session.get(WorkoutExercise, workout_exercise_id)
    if we is None or we.workout_id != workout_id:
        raise ApiError("Workout exercise not found", 404)
    body = request.get_json(force=True) or {}
    if "notes" in body:
        we.notes = (body["notes"] or "").strip() or None
    if "superset_group" in body:
        if body["superset_group"] is not None:
            raise ApiError("Use POST /workouts/:id/exercises/link to form a superset pair", 400)
        unlink(we.workout.exercises, we.id)
    db.session.commit()
    return jsonify(serialize_workout(we.workout))


@bp.post("/workouts/<int:workout_id>/exercises/link")
def link_workout_exercises(workout_id):
    """Pairs two of this workout's exercises into a superset -- forcing the same set count on
    both from this point on (see services/supersets.py). They must be adjacent; the UI only ever
    offers this between neighboring exercise cards, so a pairing is always visually a block."""
    workout = db.session.get(Workout, workout_id)
    if workout is None:
        raise ApiError("Workout not found", 404)
    body = request.get_json(force=True) or {}
    by_id = {we.id: we for we in workout.exercises}
    first, second = by_id.get(body.get("first_id")), by_id.get(body.get("second_id"))
    if first is None or second is None:
        raise ApiError("first_id and second_id must be exercises in this workout", 400)
    if abs(first.position - second.position) != 1:
        raise ApiError("Only adjacent exercises can be paired into a superset", 400)

    link_pair(workout.exercises, first.id, second.id)
    equalize_workout_superset_sets(workout)
    db.session.commit()
    return jsonify(serialize_workout(workout))


@bp.delete("/workouts/<int:workout_id>/exercises/<int:workout_exercise_id>")
def remove_workout_exercise(workout_id, workout_exercise_id):
    we = db.session.get(WorkoutExercise, workout_exercise_id)
    if we is None or we.workout_id != workout_id:
        raise ApiError("Workout exercise not found", 404)
    workout = we.workout
    db.session.delete(we)
    db.session.flush()
    # Removing the middle of a 3+ superset can leave the rest still contiguous (fine, stays
    # linked); normalize in case it doesn't.
    normalize_superset_groups(sorted(workout.exercises, key=lambda e: e.position))
    db.session.commit()
    return "", 204


@bp.post("/workout-exercises/<int:workout_exercise_id>/sets")
def add_set(workout_exercise_id):
    we = db.session.get(WorkoutExercise, workout_exercise_id)
    if we is None:
        raise ApiError("Workout exercise not found", 404)
    body = request.get_json(silent=True) or {}

    previous = we.sets[-1] if we.sets else None
    previous_is_real = previous is not None and (
        previous.weight is not None or previous.reps is not None or previous.duration_seconds is not None
    )
    if previous_is_real:
        # Fast repeat-set entry: the previous set already has something real to copy (below).
        planned = None
    elif previous is not None:
        # The previous set is itself still just a suggestion (added but not yet filled in or
        # completed) -- carry the same suggestion forward, so a run of sets added before any of
        # them are touched all show the same planned value, same as a template start's working
        # sets all do. Without this, only the first of the run would (previous.weight/reps are
        # still null, so there'd be nothing to copy and no suggestion to carry).
        planned = {
            "weight": previous.planned_weight,
            "weight_unit": previous.planned_weight_unit,
            "reps": previous.planned_reps,
            "duration_seconds": previous.planned_duration_seconds,
            "is_progressed": previous.planned_is_progressed,
        }
    else:
        # The exercise's first set this session (e.g. just added mid-workout, not started from
        # a template) -- nothing real to copy from within this workout yet, so suggest it the
        # same way starting from a template does: progressive overload from the exercise's last
        # session, as a planned (ghost) value, not a real one (see sets_plan.py).
        planned = plan_sets(SetPlanSpec(exercise_id=we.exercise_id, target_sets=1))[0]
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
        # Deliberately not copied from the previous set (unlike weight): an
        # empty rest field shows ghost text derived from the sets before it,
        # so a later change to one set's rest carries to the sets after it.
        rest_seconds=body.get("rest_seconds"),
        completed=body.get("completed", False),
        planned_weight=planned["weight"] if planned else None,
        planned_weight_unit=planned["weight_unit"] if planned else None,
        planned_reps=planned["reps"] if planned else None,
        planned_duration_seconds=planned["duration_seconds"] if planned else None,
        planned_is_progressed=planned["is_progressed"] if planned else False,
    )
    db.session.add(new_set)
    db.session.flush()
    if we.superset_group is not None:
        # A superset's members always have the same set count -- adding one here adds a
        # (blank) one to every other member too, rather than letting them drift apart.
        # `we.sets` was loaded before the flush above, so it needs refreshing to count the
        # set just added -- setting workout_exercise_id directly (rather than appending to
        # the collection) doesn't update it in place.
        db.session.expire(we, ["sets"])
        equalize_workout_superset_sets(we.workout)
    db.session.commit()
    return jsonify(serialize_set(new_set)), 201


@bp.patch("/sets/<int:set_id>")
def update_set(set_id):
    s = db.session.get(WorkoutSet, set_id)
    if s is None:
        raise ApiError("Set not found", 404)
    body = request.get_json(force=True) or {}
    was_completed = s.completed

    for field in (
        "weight",
        "weight_unit",
        "reps",
        "duration_seconds",
        "distance_meters",
        "rest_seconds",
        "is_warmup",
        "is_dropset",
        "rpe",
        "completed",
    ):
        if field in body:
            setattr(s, field, body[field])

    if s.completed and not was_completed:
        # Completing a set makes its planned values real, for any field left empty.
        if s.weight is None and s.planned_weight is not None:
            s.weight, s.weight_unit = s.planned_weight, s.planned_weight_unit
        if s.reps is None:
            s.reps = s.planned_reps
        if s.duration_seconds is None:
            s.duration_seconds = s.planned_duration_seconds
        s.planned_weight = s.planned_weight_unit = s.planned_reps = s.planned_duration_seconds = None
        s.planned_is_progressed = False

    db.session.commit()
    return jsonify(serialize_set(s))


@bp.delete("/sets/<int:set_id>")
def delete_set(set_id):
    s = db.session.get(WorkoutSet, set_id)
    if s is None:
        raise ApiError("Set not found", 404)
    we = s.workout_exercise
    group, position = we.superset_group, s.position
    db.session.delete(s)
    if group is not None:
        # Keep the superset's members at the same set count: deleting a round removes it from
        # every member, not just the one it was deleted from.
        for sibling in we.workout.exercises:
            if sibling.id == we.id or sibling.superset_group != group:
                continue
            sibling_set = next((x for x in sibling.sets if x.position == position), None)
            if sibling_set is not None:
                db.session.delete(sibling_set)
    db.session.commit()
    return "", 204
