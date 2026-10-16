"""Per-muscle strength score.

Spec: docs/source/features/strength_score.rst. In short: each completed workout is
reduced to one value per muscle and per kind of measurement (see below). Each value is
compared with an exponential moving average of that muscle's earlier workouts. A ratio
above 1.0 means stronger than before.

Exercises only report their muscles and sets. The score never looks at an exercise's
own history.

Two kinds of measurement are scored, each with its own baseline per muscle so the
scales never mix:
- "load": weight x reps, as estimated 1RM in kg (weight_reps exercises, and
  bodyweight_reps exercises using logged body weight + any added weight as the load);
- "hold": how long a timed set lasted, in seconds (time exercises, except Mobility).
Cardio is never scored.
"""

import math
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.orm import selectinload

from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise
from app.serializers import canonical_muscle_slug
from app.services.dates import local_date
from app.services.units import convert_weight

EMA_SPAN = 5
ALPHA = 2 / (EMA_SPAN + 1)
# Prior workouts with data for a muscle (per kind of measurement) before it gets a score.
MIN_HISTORY = 3
TOP_SETS = 3
MAX_REPS = 10
PRIMARY_WEIGHT = 1.0
SECONDARY_WEIGHT = 0.5

LOAD = "load"
HOLD = "hold"
# Stretches are timed but aren't strength work.
HOLD_EXCLUDED_GROUPS = {"Mobility"}


@dataclass
class _Baseline:
    ema: float
    count: int


def _estimated_one_rm_kg(weight_kg: float, reps: int) -> float:
    # Epley, the same formula as WorkoutSet.estimated_one_rm.
    if reps == 1:
        return weight_kg
    return weight_kg * (1 + reps / 30.0)


def _is_working_set(s, bodyweight: bool = False) -> bool:
    if not (
        s.completed
        and not s.is_warmup
        and not s.is_dropset
        and s.weight is not None
        and s.reps is not None
        and 1 <= s.reps <= MAX_REPS
        and s.weight_unit in ("lbs", "kg")
    ):
        return False
    # A plain weight_reps set with weight 0 logged nothing real -- but 0 is the ordinary,
    # expected value for a bodyweight_reps set's *added* weight (most never add any), so it
    # doesn't disqualify the set there; body weight itself supplies the real load.
    return bodyweight or float(s.weight) > 0


def body_weight_kg_on(when) -> float | None:
    """The logged body weight (kg) as of a given moment -- the most recent BodyweightEntry on
    or before that date, or (if the workout predates every entry) the earliest one ever logged,
    since body weight moves slowly enough day to day that the nearest known value is a
    reasonable stand-in. None only if body weight has never been logged at all -- then a
    bodyweight exercise's sets have no load to estimate from and simply aren't scored, the
    same as before body weight was factored in at all."""
    from app.models.bodyweight import BodyweightEntry  # local import avoids a circular import

    day = local_date(when)
    entry = (
        BodyweightEntry.query.filter(BodyweightEntry.recorded_at <= day)
        .order_by(BodyweightEntry.recorded_at.desc())
        .first()
    ) or BodyweightEntry.query.order_by(BodyweightEntry.recorded_at.asc()).first()
    if entry is None:
        return None
    return convert_weight(float(entry.weight), entry.unit, "kg")


def _is_hold_set(s) -> bool:
    return (
        s.completed
        and not s.is_warmup
        and not s.is_dropset
        and s.duration_seconds is not None
        and s.duration_seconds > 0
    )


def _muscle_weights(exercise: ExerciseTemplate) -> dict[str, float]:
    """Canonical muscle slug -> how directly this exercise works it. A muscle listed
    as both is primary."""
    weights = {}
    for raw in exercise.secondary_muscles or []:
        weights[canonical_muscle_slug(raw)] = SECONDARY_WEIGHT
    for raw in exercise.primary_muscles or []:
        weights[canonical_muscle_slug(raw)] = PRIMARY_WEIGHT
    return weights


def _measurement_kind(exercise: ExerciseTemplate) -> str | None:
    """Which kind of measurement an exercise is scored as, or None if it isn't scored."""
    if exercise.is_stretch:
        return None
    if exercise.tracking_type in ("weight_reps", "bodyweight_reps"):
        return LOAD
    if exercise.tracking_type == "time":
        return HOLD
    return None  # cardio and anything else


def muscle_shares(exercise: ExerciseTemplate) -> dict[str, float]:
    """Canonical muscle slug -> the share of an exercise's work that muscle does. The
    muscle weights are scaled to add up to 1, so a bench press gives its primary muscle
    most of the credit and its secondary muscles a smaller part. The total is never more
    than the lift itself."""
    weights = _muscle_weights(exercise)
    total = sum(weights.values())
    return {slug: w / total for slug, w in weights.items()} if total else {}


def _track_values(workout: Workout) -> dict[tuple[str, str], float]:
    """(muscle slug, kind) -> this workout's value. Each set's metric (estimated 1RM for
    load, duration for holds) is credited to each muscle in proportion to that muscle's
    share of the exercise. The value is the mean of the TOP_SETS best credited sets."""
    candidates = defaultdict(list)  # (slug, kind) -> [credited metric]
    body_weight_kg: float | None = None
    body_weight_checked = False
    for we in workout.exercises:
        ex = we.exercise
        if ex is None:
            continue
        kind = _measurement_kind(ex)
        if kind is None:
            continue
        is_bodyweight = ex.tracking_type == "bodyweight_reps"
        if is_bodyweight and not body_weight_checked:
            # Looked up once per workout, not per set/exercise -- body weight doesn't change
            # within a session, and most workouts have no bodyweight exercise at all.
            body_weight_kg = body_weight_kg_on(workout.started_at)
            body_weight_checked = True
        shares = muscle_shares(ex)
        for s in we.sets:
            if kind == LOAD and _is_working_set(s, bodyweight=is_bodyweight):
                added_kg = convert_weight(float(s.weight), s.weight_unit, "kg")
                if is_bodyweight:
                    if body_weight_kg is None:
                        continue  # never logged a body weight -- no load to credit this with
                    weight_kg = body_weight_kg + added_kg
                else:
                    weight_kg = added_kg
                metric = _estimated_one_rm_kg(weight_kg, s.reps)
            elif kind == HOLD and _is_hold_set(s):
                metric = float(s.duration_seconds)
            else:
                continue
            for slug, share in shares.items():
                candidates[(slug, kind)].append(metric * share)

    values = {}
    for key, found in candidates.items():
        top = sorted(found, reverse=True)[:TOP_SETS]
        values[key] = sum(top) / len(top)
    return values


def workout_muscle_values(workout: Workout) -> dict[str, float]:
    """The load value per muscle (kg), for workouts with weight_reps or bodyweight_reps
    exercises."""
    return {slug: v for (slug, kind), v in _track_values(workout).items() if kind == LOAD}


def _planned_muscles(workout: Workout) -> set[str]:
    """Muscles of exercises with no completed set yet: planned, or skipped. Every exercise the
    generator treats as strength work counts, including bodyweight and timed core work. Cardio and
    stretches don't, since they don't work a muscle in the strength sense."""
    planned = set()
    for we in workout.exercises:
        ex = we.exercise
        if ex is None or any(s.completed for s in we.sets):
            continue
        if ex.tracking_type == "cardio" or ex.is_stretch:
            continue
        planned.update(_muscle_weights(ex))
    return planned


def _fold(baselines: dict[tuple[str, str], _Baseline], values: dict[tuple[str, str], float]) -> None:
    """Fold one workout's values into the baselines."""
    for key, value in values.items():
        b = baselines.get(key)
        if b is None:
            baselines[key] = _Baseline(ema=value, count=1)
        else:
            b.ema = ALPHA * value + (1 - ALPHA) * b.ema
            b.count += 1


def build_baselines(history: list[Workout]) -> dict[tuple[str, str], _Baseline]:
    """Fold earlier workouts, oldest first, into a moving average per (muscle, kind)."""
    baselines: dict[tuple[str, str], _Baseline] = {}
    for workout in history:
        _fold(baselines, _track_values(workout))
    return baselines


def _status(
    values: dict[tuple[str, str], float],
    planned: set[str],
    baselines: dict[tuple[str, str], _Baseline],
) -> dict:
    """A workout's score and each muscle's status. A muscle's ratio is the geometric mean
    of its scored kinds (load and hold), so each kind is compared on its own scale."""
    per_muscle: dict[str, list[float]] = defaultdict(list)
    worked = set()
    for key, value in values.items():
        slug = key[0]
        worked.add(slug)
        b = baselines.get(key)
        if b is None or b.count < MIN_HISTORY:
            continue
        per_muscle[slug].append(value / b.ema)

    muscles = {}
    for slug in worked:
        ratios = per_muscle.get(slug)
        if ratios:
            ratio = math.exp(sum(math.log(r) for r in ratios) / len(ratios))
            muscles[slug] = {"status": "scored", "ratio": ratio}
        else:
            muscles[slug] = {"status": "no_baseline", "ratio": None}

    for slug in planned - worked:
        muscles[slug] = {"status": "pending", "ratio": None}

    scored = [m["ratio"] for m in muscles.values() if m["status"] == "scored"]
    score = None
    if scored:
        # Geometric mean: a +20% and a -20% muscle cancel to 0.96, so 1.0 means no net change.
        score = math.exp(sum(math.log(r) for r in scored) / len(scored))
    return {"score": score, "muscles": muscles}


def score_workout(workout: Workout, history: list[Workout]) -> dict:
    """Score `workout` against `history`, the completed workouts before it (oldest
    first). Returns the workout score (None until some muscle has enough history)
    and each muscle's status: "scored" (with its ratio), "no_baseline" (worked, but
    too little history), or "pending" (planned or skipped, not worked yet)."""
    return _status(_track_values(workout), _planned_muscles(workout), build_baselines(history))


def history_before(workout: Workout) -> list[Workout]:
    """Completed workouts that started before `workout`, oldest first."""
    return (
        Workout.query.options(*_LOAD_OPTIONS)
        .filter(
            Workout.completed_at.isnot(None),
            Workout.started_at < workout.started_at,
            Workout.id != workout.id,
        )
        .order_by(Workout.started_at, Workout.id)
        .all()
    )


def completed_workouts() -> list[Workout]:
    """Every completed workout, oldest first, with what scoring reads already loaded."""
    return (
        Workout.query.options(*_LOAD_OPTIONS)
        .filter(Workout.completed_at.isnot(None))
        .order_by(Workout.started_at, Workout.id)
        .all()
    )


_LOAD_OPTIONS = (
    selectinload(Workout.exercises).selectinload(WorkoutExercise.sets),
    selectinload(Workout.exercises)
    .selectinload(WorkoutExercise.exercise)
    .selectinload(ExerciseTemplate.app_muscle_group),
)


def strength_for_workout(workout: Workout) -> dict:
    return score_workout(workout, history_before(workout))


def score_series(workouts: list[Workout]) -> list[dict]:
    """The strength status of each of `workouts` (oldest first), in one pass.

    Each entry matches score_workout(w, history_before(w)) for that workout, without
    replaying the history for each one. Entries carry the workout's id, start time,
    template id, score, and per-muscle statuses.
    """
    baselines: dict[tuple[str, str], _Baseline] = {}
    series = []
    for workout in workouts:
        values = _track_values(workout)
        status = _status(values, _planned_muscles(workout), baselines)
        series.append(
            {
                "workout_id": workout.id,
                "started_at": workout.started_at,
                "template_id": workout.template_id,
                **status,
            }
        )
        _fold(baselines, values)
    return series
