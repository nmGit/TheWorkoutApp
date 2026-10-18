from datetime import date, datetime, timedelta

from app.services.stats import compute_streak_weeks
from app.services.units import convert_weight, meters_to_unit


def test_epley_1rm_formula():
    from app.models.workout import WorkoutSet

    s = WorkoutSet(weight=200, reps=5, is_warmup=False)
    # Epley: 200 * (1 + 5/30) = 233.33...
    assert round(s.estimated_one_rm(), 2) == round(200 * (1 + 5 / 30.0), 2)


def test_1rm_single_rep_is_raw_weight():
    from app.models.workout import WorkoutSet

    s = WorkoutSet(weight=225, reps=1, is_warmup=False)
    assert s.estimated_one_rm() == 225.0


def test_1rm_excludes_warmups():
    from app.models.workout import WorkoutSet

    s = WorkoutSet(weight=100, reps=10, is_warmup=True)
    assert s.estimated_one_rm() is None


def test_1rm_for_bodyweight_exercise_adds_logged_body_weight(app):
    from app.extensions import db
    from app.models.bodyweight import BodyweightEntry
    from app.models.exercise_template import ExerciseTemplate
    from app.models.workout import Workout, WorkoutExercise, WorkoutSet

    with app.app_context():
        db.session.add(BodyweightEntry(recorded_at=date(2026, 1, 1), weight=80, unit="kg"))
        pushup = ExerciseTemplate(name="push up", tracking_type="bodyweight_reps")
        db.session.add(pushup)
        db.session.flush()
        workout = Workout(name="w", started_at=datetime(2026, 1, 5, 9, 0, 0))
        db.session.add(workout)
        db.session.flush()
        we = WorkoutExercise(workout_id=workout.id, exercise_id=pushup.id, position=0)
        db.session.add(we)
        db.session.flush()
        # No added weight (the ordinary case) -- the real load is body weight alone.
        plain = WorkoutSet(workout_exercise_id=we.id, position=0, weight=0, weight_unit="kg", reps=8)
        # A 10kg weighted vest on top.
        weighted = WorkoutSet(workout_exercise_id=we.id, position=1, weight=10, weight_unit="kg", reps=8)
        db.session.add_all([plain, weighted])
        db.session.flush()

        assert round(plain.estimated_one_rm(), 2) == round(80 * (1 + 8 / 30.0), 2)
        assert round(weighted.estimated_one_rm(), 2) == round(90 * (1 + 8 / 30.0), 2)


def test_1rm_for_bodyweight_exercise_is_none_without_any_logged_body_weight(app):
    from app.extensions import db
    from app.models.exercise_template import ExerciseTemplate
    from app.models.workout import Workout, WorkoutExercise, WorkoutSet

    with app.app_context():
        pushup = ExerciseTemplate(name="push up", tracking_type="bodyweight_reps")
        db.session.add(pushup)
        db.session.flush()
        workout = Workout(name="w", started_at=datetime(2026, 1, 5, 9, 0, 0))
        db.session.add(workout)
        db.session.flush()
        we = WorkoutExercise(workout_id=workout.id, exercise_id=pushup.id, position=0)
        db.session.add(we)
        db.session.flush()
        s = WorkoutSet(workout_exercise_id=we.id, position=0, weight=0, weight_unit="kg", reps=8)
        db.session.add(s)
        db.session.flush()

        assert s.estimated_one_rm() is None


def test_default_metric_for_bodyweight_exercise_is_est_1rm():
    from app.models.exercise_template import ExerciseTemplate
    from app.services.stats import default_metric_for

    pushup = ExerciseTemplate(name="push up", tracking_type="bodyweight_reps")
    # Volume (added weight x reps) is always zero for the common case of no added weight --
    # est_1rm, which now factors in logged body weight, is the useful default instead.
    assert default_metric_for(pushup) == "est_1rm"


def test_weight_unit_conversion_roundtrip():
    kg = convert_weight(220.462262185, "lbs", "kg")
    assert round(kg, 3) == 100.0
    back = convert_weight(kg, "kg", "lbs")
    assert round(back, 3) == round(220.462262185, 3)


def test_distance_conversion():
    assert round(meters_to_unit(1609.344, "mi"), 4) == 1.0
    assert round(meters_to_unit(1000, "km"), 4) == 1.0


def test_streak_current_week_untrained_keeps_prior_streak():
    today = date.today()
    last_week = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    streak = compute_streak_weeks({last_week, two_weeks_ago})
    assert streak == 2


def test_streak_breaks_on_gap():
    today = date.today()
    three_weeks_ago = today - timedelta(days=21)
    streak = compute_streak_weeks({today, three_weeks_ago})
    assert streak == 1


def test_streak_empty():
    assert compute_streak_weeks(set()) == 0
