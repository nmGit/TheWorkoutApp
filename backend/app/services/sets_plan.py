"""The sets a workout starts with, from a template exercise.

The template says how many sets of each kind (warm-up, working, drop) to start with. Values come from
the last completed session of that exercise:

- Warm-up and drop sets copy the same kind of set from that session, in the same position.
- Working sets follow the progression method in Settings, applied to that session's top working sets.
  With progression off, they copy the last session's working sets instead.

Warm-ups are never used to progress a load: only working sets count.
"""

from app.models.workout import Workout, WorkoutExercise
from app.models.settings import UserSettings
from app.services.units import convert_weight

DEFAULT_REP_RANGE = (8, 12)
TOP_TOLERANCE = 0.005  # sets within 0.5% of the session's top weight count as its top sets


def rep_range_or_none(text: str | None) -> tuple[int, int] | None:
    """'6-8' -> (6, 8); '10' -> (10, 10); None if the text isn't a usable range."""
    if not text:
        return None
    parts = text.replace("–", "-").split("-")
    try:
        low = int(parts[0].strip())
        high = int(parts[-1].strip())
    except ValueError:
        return None
    if low < 1 or high < low or high > 100:
        return None
    return low, high


def parse_rep_range(text: str | None) -> tuple[int, int]:
    """Like rep_range_or_none, but anything unusable gives the default range."""
    return rep_range_or_none(text) or DEFAULT_REP_RANGE


def _last_sets_by_kind(exercise_id: int) -> dict[str, list]:
    last = (
        WorkoutExercise.query.join(Workout, Workout.id == WorkoutExercise.workout_id)
        .filter(WorkoutExercise.exercise_id == exercise_id, Workout.completed_at.isnot(None))
        .order_by(Workout.started_at.desc(), Workout.id.desc())
        .first()
    )
    kinds: dict[str, list] = {"warmup": [], "working": [], "drop": []}
    if last is None:
        return kinds
    for s in last.sets:  # ordered by position
        if not s.completed:
            continue
        kinds["warmup" if s.is_warmup else "drop" if s.is_dropset else "working"].append(s)
    return kinds


def progress_working(working: list, rep_range: tuple[int, int], settings: UserSettings):
    """The next working set's (weight, unit, reps) from last session's working sets, or None if there is
    nothing to progress from (no weights logged) or progression is off."""
    if settings.progression_method == "off":
        return None
    logged = [s for s in working if s.weight is not None and s.reps is not None and float(s.weight) > 0]
    if not logged:
        return None

    low, high = rep_range
    top_kg = max(convert_weight(float(s.weight), s.weight_unit, "kg") for s in logged)
    top = [
        s
        for s in logged
        if convert_weight(float(s.weight), s.weight_unit, "kg") >= top_kg * (1 - TOP_TOLERANCE)
    ]
    unit = settings.weight_unit
    step = settings.load_step_lb if unit == "lbs" else settings.load_step_kg
    top_weight = convert_weight(top_kg, "kg", unit)
    # Reached the top of the range on every top set: time to add load.
    reached = all(s.reps >= high for s in top)
    fewest = min(s.reps for s in top)

    if settings.progression_method == "linear":
        weight = top_weight + step if reached else top_weight
        return round(weight, 2), unit, high

    # Double progression: first add reps within the range, then add load and start again at the bottom.
    if reached:
        return round(top_weight + step, 2), unit, low
    return round(top_weight, 2), unit, min(high, max(low, fewest + 1))


def plan_sets(template_exercise) -> list[dict]:
    """Field values for each set a workout starts with, in the order: warm-ups, working, drops."""
    settings = UserSettings.get()
    previous = _last_sets_by_kind(template_exercise.exercise_id)
    # The exercise's own range wins; otherwise the default range from Settings.
    rep_range = parse_rep_range(template_exercise.target_reps or settings.default_rep_range)
    progressed = progress_working(previous["working"], rep_range, settings)

    counts = [
        ("warmup", template_exercise.warmup_sets or 0),
        ("working", template_exercise.target_sets or 1),
        ("drop", template_exercise.drop_sets or 0),
    ]
    planned = []
    for kind, count in counts:
        copies = previous[kind]
        for i in range(count):
            if kind == "working" and progressed is not None:
                weight, unit, reps = progressed
                planned.append({
                    "is_warmup": False,
                    "is_dropset": False,
                    "weight": weight,
                    "weight_unit": unit,
                    "reps": reps,
                    "duration_seconds": None,
                })
                continue
            if i < len(copies):
                source = copies[i]
            elif kind == "working" and copies:
                source = copies[-1]
            else:
                source = None
            planned.append({
                "is_warmup": kind == "warmup",
                "is_dropset": kind == "drop",
                "weight": source.weight if source else None,
                "weight_unit": source.weight_unit if source else None,
                "reps": source.reps if source else None,
                "duration_seconds": source.duration_seconds if source else None,
            })
    return planned
