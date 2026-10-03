import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from scripts.import_strong_csv import (
    _f,
    _i,
    group_by_workout,
    normalize,
    parse_equipment_suffix,
    resolve_exercise,
)


def test_normalize_ignores_equipment_suffix_and_punctuation():
    assert normalize("V Up") == normalize("V-Up") == "vup"
    assert normalize("Squat (Barbell)") == normalize("Squat") == "squat"


def test_parse_equipment_suffix():
    assert parse_equipment_suffix("Bicep Curl (Dumbbell)") == "Dumbbell"
    assert parse_equipment_suffix("Squat") is None


def test_numeric_parsing_treats_blank_as_none():
    assert _f("") is None
    assert _f("47.62719885") == 47.62719885
    assert _i("") is None
    assert _i("8") == 8
    assert _i("8.0") == 8


def test_group_by_workout_preserves_row_order():
    rows = [
        {"Workout #": "1", "Exercise Name": "Squat"},
        {"Workout #": "2", "Exercise Name": "Bench"},
        {"Workout #": "1", "Exercise Name": "Deadlift"},
    ]
    grouped = group_by_workout(rows)
    assert list(grouped.keys()) == ["1", "2"]
    assert [r["Exercise Name"] for r in grouped["1"]] == ["Squat", "Deadlift"]


def test_resolve_exercise_exact_match(app, bench_press):
    resolved = resolve_exercise("bench press", {})
    assert resolved.id == bench_press.id


def test_resolve_exercise_base_name_reconciles_equipment(app, chest_group):
    ex = ExerciseTemplate(
        name="Goblet Squat",
        muscle_group_id=chest_group.id,
        equipment="dumbbell",
        tracking_type="weight_reps",
        is_custom=False,
    )
    db.session.add(ex)
    db.session.commit()

    resolved = resolve_exercise("Goblet Squat (Kettlebell)", {})
    assert resolved.id == ex.id
    assert resolved.equipment == "kettlebell"


def test_resolve_exercise_unknown_raises(app, bench_press):
    try:
        resolve_exercise("Some Brand New Machine Nobody Seeded", {})
        assert False, "expected LookupError"
    except LookupError:
        pass


def test_resolve_exercise_uses_cache(app, bench_press):
    cache = {}
    first = resolve_exercise("Bench Press", cache)
    assert cache["Bench Press"] is first
    # A second call with the same name should hit the cache, not the DB,
    # so it still resolves correctly even if called many times per import.
    second = resolve_exercise("Bench Press", cache)
    assert second is first


def test_resolve_exercise_matches_an_alias(app, bench_press):
    # A name the exercise was merged away from (or is also known by) must
    # still resolve, otherwise the next Strong export would fail on it.
    bench_press.aliases = ["Strict Bench (Barbell)"]
    db.session.commit()
    assert resolve_exercise("strict bench (barbell)", {}).id == bench_press.id
    assert resolve_exercise("Strict Bench (Barbell)", {}).id == bench_press.id
