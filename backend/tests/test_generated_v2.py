from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.generated_v2 import generated_rir, rep_weight, score_series_v2

START = datetime(2026, 3, 2, 9, 0, 0)


def test_rep_weight_is_full_to_8_and_half_at_15():
    assert rep_weight(1) == 1.0
    assert rep_weight(8) == 1.0
    assert rep_weight(15) == pytest.approx(0.5)
    assert rep_weight(11) == pytest.approx(1 - 0.5 * 3 / 7)


def test_generated_rir_uses_the_reference_not_the_set_itself():
    # 100 kg for 5 against a reference equal to that set's own e1RM: about failure, RIR near 0.
    assert generated_rir(5, 100, 100 * (1 + 5 / 30)) == pytest.approx(0, abs=0.01)
    # 60 kg for 10 reps against the same reference is far from failure: capped at 5.
    assert generated_rir(10, 60, 100 * (1 + 5 / 30)) == 5.0


def _exercise(name, primary, tracking="weight_reps"):
    ex = ExerciseTemplate(name=name, tracking_type=tracking, primary_muscles=primary, secondary_muscles=[], is_custom=False)
    db.session.add(ex)
    db.session.flush()
    return ex


def _session(ex, day, kg, reps=5):
    started = START + timedelta(days=day)
    w = Workout(name=f"{ex.name} {day}", started_at=started, completed_at=started + timedelta(minutes=40))
    db.session.add(w)
    db.session.flush()
    we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, position=0)
    db.session.add(we)
    db.session.flush()
    db.session.add(WorkoutSet(workout_exercise_id=we.id, position=0, weight=kg, weight_unit="kg", reps=reps, completed=True))
    db.session.flush()
    return w


def test_exercises_are_not_pooled_so_a_swap_does_not_move_the_muscle(app):
    """Triceps is worked by a heavy bench and a light pushdown. Alternating them must not
    make the triceps ratio swing, because each exercise has its own baseline."""
    with app.app_context():
        bench = _exercise("bench", ["triceps_brachii"])
        pushdown = _exercise("pushdown", ["triceps_brachii"])
        sessions = []
        for day in range(6):
            sessions.append(_session(bench, day * 2, 100))
            sessions.append(_session(pushdown, day * 2 + 1, 40))
        db.session.commit()

        series = score_series_v2(sessions)
        late = [
            p["muscles"]["triceps_brachii"]["ratio"]
            for p in series[4:]
            if p["muscles"].get("triceps_brachii", {}).get("status") == "scored"
        ]
        assert late
        # Each exercise is steady, so each ratio stays at 1 even though the loads differ 2.5x.
        assert all(r == pytest.approx(1.0, rel=0.01) for r in late)


def test_a_new_exercise_is_unscored_until_it_has_history(app):
    with app.app_context():
        curl = _exercise("curl", ["biceps_brachii"])
        sessions = [_session(curl, d, 20) for d in range(4)]
        db.session.commit()
        series = score_series_v2(sessions)
        # Worked but still in its warm-up: no ratio yet, and no score.
        assert set(series[0]["muscles"]) == {"biceps_brachii"}
        assert series[0]["muscles"]["biceps_brachii"]["status"] == "no_baseline"
        assert series[0]["score"] is None
        assert series[2]["muscles"]["biceps_brachii"]["status"] == "no_baseline"
        assert series[3]["muscles"]["biceps_brachii"]["status"] == "scored"
