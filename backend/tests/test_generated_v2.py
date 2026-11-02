import math
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.generated_v2 import _exercise_sessions, generated_rir, rep_weight, score_series_v2

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


def _exercise(name, primary, tracking="weight_reps", group=None):
    group_id = None
    if group is not None:
        g = MuscleGroup.query.filter_by(name=group).first()
        if g is None:
            g = MuscleGroup(name=group, display_order=0)
            db.session.add(g)
            db.session.flush()
        group_id = g.id
    ex = ExerciseTemplate(
        name=name, tracking_type=tracking, muscle_group_id=group_id,
        primary_muscles=primary, secondary_muscles=[],
    )
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


def _multi_set_session(ex, day, sets):
    """Like `_session`, but with an arbitrary list of sets -- each a (weight, reps) pair in kg,
    or a dict of extra WorkoutSet fields (e.g. `is_warmup`, `duration_seconds`)."""
    started = START + timedelta(days=day)
    w = Workout(name=f"{ex.name} {day}", started_at=started, completed_at=started + timedelta(minutes=40))
    db.session.add(w)
    db.session.flush()
    we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, position=0)
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
    db.session.flush()
    return w


def _e1rm(kg, reps):
    return kg * (1 + reps / 30)


def _multi_exercise_session(day, specs):
    """A workout with several exercises at once -- each of `specs` a (exercise, kg, reps)
    triple. Returns (workout, [that exercise's WorkoutExercise id, in the same order])."""
    started = START + timedelta(days=day)
    w = Workout(name=f"multi {day}", started_at=started, completed_at=started + timedelta(minutes=40))
    db.session.add(w)
    db.session.flush()
    we_ids = []
    for position, (ex, kg, reps) in enumerate(specs):
        we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, position=position)
        db.session.add(we)
        db.session.flush()
        db.session.add(
            WorkoutSet(workout_exercise_id=we.id, position=0, weight=kg, weight_unit="kg", reps=reps, completed=True)
        )
        we_ids.append(we.id)
    db.session.flush()
    return w, we_ids


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


def test_exercise_session_takes_the_top_three_sets_and_ignores_warmups_dropsets_and_over_cap_reps(app):
    with app.app_context():
        bench = _exercise("bench", ["pectoralis_major"])
        w = _multi_set_session(
            bench,
            0,
            [
                (100, 5),
                (110, 5),
                (120, 5),
                (130, 5),  # the top three are 130, 120, 110
                {"weight": 200, "reps": 5, "is_warmup": True},  # warm-up: ignored
                {"weight": 200, "reps": 5, "is_dropset": True},  # drop set: ignored
                {"weight": 90, "reps": 20},  # over the rep cap (15): ignored
                {"weight": 300, "reps": 5, "completed": False},  # not completed: ignored
            ],
        )
        db.session.commit()
        sessions = _exercise_sessions(w, {})

    assert len(sessions) == 1
    top = [_e1rm(130, 5), _e1rm(120, 5), _e1rm(110, 5)]
    assert sessions[0].value == pytest.approx(sum(top) / 3)
    assert sessions[0].counting_sets == 4  # the 4 legitimate sets, not just the top 3 counted


def test_pounds_are_converted_to_kg_before_scoring(app):
    with app.app_context():
        bench = _exercise("bench", ["pectoralis_major"])
        w = _multi_set_session(bench, 0, [{"weight": 220.462262, "reps": 5, "weight_unit": "lbs"}])
        db.session.commit()
        sessions = _exercise_sessions(w, {})

    assert sessions[0].value == pytest.approx(_e1rm(100, 5), rel=1e-4)


def test_timed_holds_get_scored_on_their_own_history(app):
    """A time-tracked exercise (e.g. a plank) scores on duration, same shape as a lift scores
    on estimated 1RM -- see HOLD in generated_v2.py/_exercise_sessions."""
    with app.app_context():
        plank = _exercise("plank", ["rectus_abdominis"], tracking="time", group="Core")
        sessions = [
            _multi_set_session(plank, d, [{"duration_seconds": duration}])
            for d, duration in enumerate([60, 65, 70, 80])
        ]
        db.session.commit()
        series = score_series_v2(sessions)

    assert series[0]["muscles"]["rectus_abdominis"]["status"] == "no_baseline"
    # Held longer than the recent sessions: an improvement, same as more weight would be.
    assert series[3]["muscles"]["rectus_abdominis"]["status"] == "scored"
    assert series[3]["muscles"]["rectus_abdominis"]["ratio"] > 1.0


def test_exercise_contribution_sums_to_the_workout_score_and_is_attributed_correctly(app):
    """Each exercise block's own share of the workout score (see V2Series.step's `exercises`)
    is additive in log space -- summing every exercise's contribution reproduces log(score)
    exactly -- and is keyed by WorkoutExercise id, not exercise_ref, so two different
    exercises in the same workout each get their own, correctly attributed, number."""
    with app.app_context():
        bench = _exercise("bench", ["pectoralis_major"])
        curl = _exercise("curl", ["biceps_brachii"])
        workouts = [_session(bench, day, 100) for day in range(3)]
        workouts += [_session(curl, day, 20) for day in range(3)]
        combined, (bench_we_id, curl_we_id) = _multi_exercise_session(10, [(bench, 110, 5), (curl, 22, 5)])
        workouts.append(combined)
        db.session.commit()
        workouts.sort(key=lambda w: w.started_at)

        series = score_series_v2(workouts)
        point = next(p for p in series if p["workout_id"] == combined.id)

    assert point["score"] is not None
    assert set(point["exercises"]) == {bench_we_id, curl_we_id}
    assert all(v != 0 for v in point["exercises"].values())
    total_contribution = sum(point["exercises"].values()) / 100
    assert total_contribution == pytest.approx(math.log(point["score"]), abs=0.01)


def test_an_exercise_with_no_scored_muscle_contributes_nothing(app):
    """An exercise still in its own warm-up period (no baseline yet) doesn't show up in
    `exercises` at all -- it moves nothing, so there's nothing to show a badge for."""
    with app.app_context():
        curl = _exercise("curl", ["biceps_brachii"])
        sessions = [_session(curl, d, 20) for d in range(4)]
        db.session.commit()
        series = score_series_v2(sessions)

    assert series[0]["exercises"] == {}
    assert series[2]["exercises"] == {}  # still below MIN_HISTORY


def test_cardio_and_mobility_stretches_are_not_scored(app):
    """Cardio is never strength work, and a Mobility-group hold is a stretch, not a plank --
    see HOLD_EXCLUDED_GROUPS in generated_v2.py. Neither should produce an ExerciseSession at
    all (not even an unscored one), so neither ever shows up as a muscle entry."""
    with app.app_context():
        cardio = _exercise("stair stepper", ["quadriceps"], tracking="cardio", group="Cardio")
        stretch = _exercise("hamstring stretch", ["hamstrings"], tracking="time", group="Mobility")
        w_cardio = _multi_set_session(cardio, 0, [{"duration_seconds": 900}])
        w_stretch = _multi_set_session(stretch, 1, [{"duration_seconds": 60}])
        db.session.commit()

        assert _exercise_sessions(w_cardio, {}) == []
        assert _exercise_sessions(w_stretch, {}) == []
