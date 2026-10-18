"""When each muscle was last worked. The one source for recency: the body diagram's recency
colours and the planner's choice of what to train both read from here."""

from collections import defaultdict
from datetime import date

from app.extensions import db
from app.models.muscle import ExerciseMuscle, Muscle
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.dates import local_date


def last_trained_dates() -> dict[str, date]:
    """Muscle slug -> local date of its last completed working set. Stretches don't count, and a
    muscle that has never been worked isn't in the result.

    Catalog exercises (workout_exercises.exercise_id) and custom ones (.custom_exercise_id) are
    looked up separately rather than with one joined query -- the two live in different
    databases now (see docs/data_model.rst "Database split"), and SQLite can't join across them.
    """
    from app.models.exercise_template import CustomExerciseTemplate, ExerciseTemplate

    stretch_ids = {ex.id for ex in ExerciseTemplate.query.all() if ex.is_stretch}
    custom_stretch_ids = {ex.id for ex in CustomExerciseTemplate.query.all() if ex.is_stretch}

    rows = (
        db.session.query(Workout.started_at, WorkoutExercise.exercise_id, WorkoutExercise.custom_exercise_id)
        .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
        .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .filter(
            Workout.completed_at.isnot(None),
            WorkoutSet.completed.is_(True),
            WorkoutSet.is_warmup.is_(False),
            WorkoutSet.is_dropset.is_(False),
        )
        .distinct()
        .all()
    )

    catalog_ids = {eid for _, eid, _ in rows if eid is not None and eid not in stretch_ids}
    muscles_by_catalog_id: dict[int, list[str]] = defaultdict(list)
    if catalog_ids:
        for exercise_id, slug in (
            db.session.query(ExerciseMuscle.exercise_id, Muscle.slug)
            .join(Muscle, Muscle.id == ExerciseMuscle.muscle_id)
            .filter(ExerciseMuscle.exercise_id.in_(catalog_ids))
            .all()
        ):
            muscles_by_catalog_id[exercise_id].append(slug)

    custom_ids = {ceid for _, _, ceid in rows if ceid is not None and ceid not in custom_stretch_ids}
    muscles_by_custom_id: dict[int, list[str]] = {}
    if custom_ids:
        for ex in CustomExerciseTemplate.query.filter(CustomExerciseTemplate.id.in_(custom_ids)).all():
            muscles_by_custom_id[ex.id] = [*ex.primary_muscles, *ex.secondary_muscles]

    last: dict[str, date] = {}
    for started, exercise_id, custom_exercise_id in rows:
        if exercise_id is not None:
            if exercise_id in stretch_ids:
                continue
            slugs = muscles_by_catalog_id.get(exercise_id, [])
        else:
            if custom_exercise_id in custom_stretch_ids:
                continue
            slugs = muscles_by_custom_id.get(custom_exercise_id, [])
        day = local_date(started)
        for slug in slugs:
            if slug not in last or day > last[slug]:
                last[slug] = day
    return last


# A muscle is in need of training once it's been this many days since it was worked. It's the
# same line the body diagram draws as fully red.
IN_NEED_DAYS = 8


def days_since_trained(today: date) -> dict[str, int]:
    """Canonical muscle slug -> days since it was last worked, for muscles that have been."""
    return {slug: (today - day).days for slug, day in last_trained_dates().items()}
