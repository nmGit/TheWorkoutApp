from datetime import date, timedelta

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
