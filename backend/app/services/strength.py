"""Shared pieces of strength scoring: muscle shares, e1RM, which sets count, and the
completed-workouts/history queries the live engine replays against.

Spec: docs/source/features/strength_score.rst. The live scoring method itself is
services/generated_v2.py; this module no longer scores a workout on its own -- an
earlier, simpler method (one EMA baseline per muscle, no per-exercise history) lived
here and was superseded by generated_v2.py's per-exercise baselines/outlier rejection/
shrinkage (see docs/source/review.rst for when and why).
"""

from sqlalchemy.orm import selectinload

from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise
from app.serializers import canonical_muscle_slug
from app.services.dates import local_date
from app.services.units import convert_weight

# Prior sessions an exercise needs (generated_v2.py) before it gets a baseline.
MIN_HISTORY = 3
PRIMARY_WEIGHT = 1.0
SECONDARY_WEIGHT = 0.5

LOAD = "load"
HOLD = "hold"
# Stretches are timed but aren't strength work.
HOLD_EXCLUDED_GROUPS = {"Mobility"}


def _estimated_one_rm_kg(weight_kg: float, reps: int) -> float:
    # Epley, the same formula as WorkoutSet.estimated_one_rm.
    if reps == 1:
        return weight_kg
    return weight_kg * (1 + reps / 30.0)


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


def muscle_shares(exercise: ExerciseTemplate) -> dict[str, float]:
    """Canonical muscle slug -> the share of an exercise's work that muscle does. The
    muscle weights are scaled to add up to 1, so a bench press gives its primary muscle
    most of the credit and its secondary muscles a smaller part. The total is never more
    than the lift itself."""
    weights = _muscle_weights(exercise)
    total = sum(weights.values())
    return {slug: w / total for slug, w in weights.items()} if total else {}


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
    # WorkoutExercise.exercise isn't an eager-loadable relationship -- it can resolve to either
    # of two tables in two different databases (see ExerciseReferenceMixin) -- so the catalog
    # side is fetched lazily instead, one query per distinct exercise id (cheap: SQLAlchemy's
    # session identity map means a given id is only ever actually fetched once no matter how
    # many WorkoutExercise rows reference it). The custom side is a real same-database
    # relationship and can still be eager-loaded.
    selectinload(Workout.exercises).selectinload(WorkoutExercise.custom_exercise),
)
