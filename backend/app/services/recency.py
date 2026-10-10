"""When each muscle was last worked. The one source for recency: the body diagram's recency
colours and the planner's choice of what to train both read from here."""

from datetime import date

from app.extensions import db
from app.models.muscle import ExerciseMuscle, Muscle
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.dates import local_date


def last_trained_dates() -> dict[str, date]:
    """Muscle slug -> local date of its last completed working set. Stretches don't count, and a
    muscle that has never been worked isn't in the result."""
    from app.models.exercise_template import ExerciseTemplate

    stretch_ids = [
        ex.id for ex in ExerciseTemplate.query.all() if ex.is_stretch
    ]
    query = (
        db.session.query(Workout.started_at, Muscle.slug)
        .join(WorkoutExercise, WorkoutExercise.workout_id == Workout.id)
        .join(ExerciseMuscle, ExerciseMuscle.exercise_id == WorkoutExercise.exercise_id)
        .join(Muscle, Muscle.id == ExerciseMuscle.muscle_id)
        .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .filter(
            Workout.completed_at.isnot(None),
            WorkoutSet.completed.is_(True),
            WorkoutSet.is_warmup.is_(False),
            WorkoutSet.is_dropset.is_(False),
        )
    )
    if stretch_ids:
        query = query.filter(WorkoutExercise.exercise_id.notin_(stretch_ids))
    rows = query.all()
    last: dict[str, date] = {}
    for started, slug in rows:
        day = local_date(started)
        if slug not in last or day > last[slug]:
            last[slug] = day
    return last


# A muscle is in need of training once it's been this many days since it was worked. It's the
# same line the body diagram draws as fully red.
IN_NEED_DAYS = 8


def days_since_trained(today: date) -> dict[str, int]:
    """Canonical muscle slug -> days since it was last worked, for muscles that have been."""
    return {slug: (today - day).days for slug, day in last_trained_dates().items()}
