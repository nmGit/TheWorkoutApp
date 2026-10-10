from datetime import datetime, timedelta

import math

import pytest

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet

START = datetime(2026, 1, 5, 9, 0, 0)


def _bench(**overrides):
    defaults = dict(
        name="bench press",
        tracking_type="weight_reps",
        primary_muscles=["pectoralis_major"],
        secondary_muscles=["triceps_brachii"],
        is_custom=False,
    )
    defaults.update(overrides)
    return ExerciseTemplate(**defaults)


def _workout(bench, day, sets, planned=None):
    """A completed bench session on `day`, with `sets` as (kg, reps) or dicts of extra
    set fields. `planned` adds a bench-like exercise with no completed sets."""
    started = START + timedelta(days=day)
    workout = Workout(name=f"day {day}", started_at=started, completed_at=started + timedelta(hours=1))
    db.session.add(workout)
    db.session.flush()
    we = WorkoutExercise(workout_id=workout.id, exercise_id=bench.id, position=0)
    db.session.add(we)
    db.session.flush()
    for i, spec in enumerate(sets):
        if isinstance(spec, tuple):
            kg, reps = spec
            spec = {"weight": kg, "reps": reps}
        db.session.add(
            WorkoutSet(
                workout_exercise_id=we.id,
                position=i,
                weight_unit=spec.pop("weight_unit", "kg"),
                completed=spec.pop("completed", True),
                **spec,
            )
        )
    if planned is not None:
        pe = WorkoutExercise(workout_id=workout.id, exercise_id=planned.id, position=1)
        db.session.add(pe)
        db.session.flush()
        db.session.add(WorkoutSet(workout_exercise_id=pe.id, position=0, weight=50, weight_unit="kg", reps=8, completed=False))
    db.session.flush()
    return workout.id


def _e1rm(kg, reps):
    return kg * (1 + reps / 30)


def test_first_workouts_have_no_score_and_then_the_baseline_compares(client, app):
    with app.app_context():
        bench = _bench()
        db.session.add(bench)
        db.session.flush()
        # One set each, so a muscle's value is that set's estimated 1RM.
        ids = [
            _workout(bench, 0, [(100, 5)]),
            _workout(bench, 1, [(105, 5)]),
            _workout(bench, 2, [(110, 5)]),
            _workout(bench, 3, [(120, 5)]),
        ]
        db.session.commit()

    first = client.get(f"/api/workouts/{ids[0]}/strength").get_json()
    assert first["score"] is None
    assert first["muscles"]["pectoralis_major"]["status"] == "no_baseline"

    third = client.get(f"/api/workouts/{ids[2]}/strength").get_json()
    assert third["score"] is None  # only two earlier workouts, below MIN_HISTORY

    # Baseline: the earlier sessions, each weighted by 0.5 ** (days ago / 21), averaged on the
    # log scale. The sessions are 1, 2 and 3 days before the fourth.
    weights = [0.5 ** (d / 21) for d in (3, 2, 1)]
    logs = [math.log(_e1rm(kg, 5)) for kg in (100, 105, 110)]
    baseline = sum(w * v for w, v in zip(weights, logs)) / sum(weights)
    change = math.log(_e1rm(120, 5)) - baseline
    # Shrinkage: the pectoral's evidence is share 2/3 x one set; the change is pulled to zero
    # by SHRINKAGE sets' worth of "no change".
    chest_evidence = 2 / 3
    from app.services.generated_v2 import SHRINKAGE

    expected = math.exp(change * chest_evidence / (chest_evidence + SHRINKAGE))
    fourth = client.get(f"/api/workouts/{ids[3]}/strength").get_json()
    assert fourth["muscles"]["pectoralis_major"]["status"] == "scored"
    assert fourth["muscles"]["pectoralis_major"]["ratio"] == pytest.approx(expected)
    # The workout score is the geometric mean over the scored muscles (chest and triceps here).
    tri_ratio = fourth["muscles"]["triceps_brachii"]["ratio"]
    assert fourth["score"] == pytest.approx(math.sqrt(expected * tri_ratio))
    # The secondary muscle is worked by the same sets, with a smaller share and so less evidence.
    tri_evidence = 1 / 3
    assert fourth["muscles"]["triceps_brachii"]["ratio"] == pytest.approx(
        math.exp(change * tri_evidence / (tri_evidence + SHRINKAGE))
    )


def test_top_sets_and_warmups_and_reps_cap(app):
    from app.services.strength import workout_muscle_values

    with app.app_context():
        bench = _bench()
        db.session.add(bench)
        db.session.flush()
        wid = _workout(
            bench,
            0,
            [
                (100, 5),
                (110, 5),
                (120, 5),
                (130, 5),  # the top three are 130, 120, 110
                {"weight": 200, "reps": 5, "is_warmup": True},  # warm-up: ignored
                {"weight": 200, "reps": 5, "is_dropset": True},  # drop set: ignored
                {"weight": 90, "reps": 20},  # over the rep cap: ignored
                {"weight": 300, "reps": 5, "completed": False},  # not completed: ignored
            ],
        )
        db.session.commit()
        workout = db.session.get(Workout, wid)
        values = workout_muscle_values(workout)

    # The bench's chest share is 1 / (1 + 0.5) = 2/3; the top three credited sets are the best three.
    top = [_e1rm(130, 5), _e1rm(120, 5), _e1rm(110, 5)]
    assert values["pectoralis_major"] == pytest.approx(sum(top) / 3 * 2 / 3)


def test_pounds_are_converted_before_scoring(app):
    from app.services.strength import workout_muscle_values

    with app.app_context():
        bench = _bench()
        db.session.add(bench)
        db.session.flush()
        wid = _workout(bench, 0, [{"weight": 220.462262, "reps": 5, "weight_unit": "lbs"}])
        db.session.commit()
        values = workout_muscle_values(db.session.get(Workout, wid))
    assert values["pectoralis_major"] == pytest.approx(_e1rm(100, 5) * 2 / 3, rel=1e-4)


def test_planned_exercise_is_pending_and_not_scored(client, app):
    with app.app_context():
        bench = _bench()
        row = _bench(name="row", primary_muscles=["lats"], secondary_muscles=[])
        db.session.add_all([bench, row])
        db.session.flush()
        for day in range(3):
            _workout(bench, day, [(100 + day, 5)])
        wid = _workout(bench, 3, [(105, 5)], planned=row)
        db.session.commit()

    body = client.get(f"/api/workouts/{wid}/strength").get_json()
    assert body["muscles"]["latissimus_dorsi"]["status"] == "pending"
    assert body["muscles"]["latissimus_dorsi"]["ratio"] is None


def test_unknown_workout_is_404(client):
    assert client.get("/api/workouts/9999/strength").status_code == 404


def test_series_matches_scoring_each_workout_on_its_own_history(app):
    from app.services.strength import completed_workouts, score_series, score_workout, history_before

    with app.app_context():
        bench = _bench()
        db.session.add(bench)
        db.session.flush()
        for day, kg in enumerate([100, 105, 98, 120, 111, 125, 130]):
            _workout(bench, day, [(kg, 5)])
        db.session.commit()

        workouts = completed_workouts()
        series = score_series(workouts)
        for workout, point in zip(workouts, series):
            expected = score_workout(workout, history_before(workout))
            if expected["score"] is None:
                assert point["score"] is None
            else:
                assert point["score"] == pytest.approx(expected["score"])
            assert point["muscles"].keys() == expected["muscles"].keys()
            for slug, status in expected["muscles"].items():
                assert point["muscles"][slug]["status"] == status["status"]
                if status["ratio"] is None:
                    assert point["muscles"][slug]["ratio"] is None
                else:
                    assert point["muscles"][slug]["ratio"] == pytest.approx(status["ratio"])


def test_strength_history_endpoint_lists_every_completed_workout(client, app):
    with app.app_context():
        bench = _bench()
        db.session.add(bench)
        db.session.flush()
        for day in range(4):
            _workout(bench, day, [(100 + day, 5)])
        db.session.commit()

    body = client.get("/api/strength/history").get_json()
    assert len(body) == 4
    assert [p["score"] for p in body[:3]] == [None, None, None]
    assert body[3]["score"] is not None
    assert body[0]["date"].endswith("+00:00")
