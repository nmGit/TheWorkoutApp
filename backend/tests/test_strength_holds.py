from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.strength import ALPHA, _track_values, score_workout, workout_muscle_values

START = datetime(2026, 2, 2, 9, 0, 0)


def _exercise(name, tracking, group, primary, secondary=()):
    g = MuscleGroup.query.filter_by(name=group).first()
    if g is None:
        g = MuscleGroup(name=group, display_order=0)
        db.session.add(g)
        db.session.flush()
    ex = ExerciseTemplate(
        name=name,
        tracking_type=tracking,
        muscle_group_id=g.id,
        primary_muscles=list(primary),
        secondary_muscles=list(secondary),
        is_custom=False,
    )
    db.session.add(ex)
    db.session.flush()
    return ex


def _session(ex, day, sets):
    """A completed session of `ex` on `day`; `sets` are dicts of WorkoutSet fields."""
    started = START + timedelta(days=day)
    w = Workout(name=f"day {day}", started_at=started, completed_at=started + timedelta(minutes=30))
    db.session.add(w)
    db.session.flush()
    we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, position=0)
    db.session.add(we)
    db.session.flush()
    for i, fields in enumerate(sets):
        db.session.add(WorkoutSet(workout_exercise_id=we.id, position=i, completed=True, **fields))
    db.session.flush()
    return w


def test_timed_holds_are_scored_on_their_own_baseline(app):
    with app.app_context():
        plank = _exercise("plank", "time", "Core", ["rectus_abdominis"], ["obliques"])
        durations = [60, 65, 70, 80]
        workouts = [_session(plank, i, [{"duration_seconds": d}]) for i, d in enumerate(durations)]
        db.session.commit()

        history = workouts[:3]
        result = score_workout(workouts[3], history)

        ema = 60.0
        for d in durations[1:3]:
            ema = ALPHA * d + (1 - ALPHA) * ema
        assert result["score"] == pytest.approx(80 / ema)
        assert result["muscles"]["rectus_abdominis"] == {"status": "scored", "ratio": pytest.approx(80 / ema)}


def test_mobility_stretches_and_cardio_are_not_scored(app):
    with app.app_context():
        stretch = _exercise("hamstring stretch", "time", "Mobility", ["hamstrings"])
        cardio = _exercise("stair stepper", "cardio", "Cardio", ["quadriceps"])
        w = _session(stretch, 0, [{"duration_seconds": 60}])
        c = _session(cardio, 1, [{"duration_seconds": 900}])
        db.session.commit()

        assert _track_values(w) == {}
        assert _track_values(c) == {}


def test_holds_and_loads_never_share_a_baseline(app):
    with app.app_context():
        bench = _exercise("bench press", "weight_reps", "Chest", ["pectoralis_major"])
        plank = _exercise("plank", "time", "Core", ["pectoralis_major"])
        lift = _session(bench, 0, [{"weight": 100, "weight_unit": "kg", "reps": 5}])
        hold = _session(plank, 1, [{"duration_seconds": 60}])
        db.session.commit()

        # The same muscle gets one load value and one hold value, kept apart.
        assert set(_track_values(hold)) == {("pectoralis_major", "hold")}
        assert set(_track_values(lift)) == {("pectoralis_major", "load")}
        # The load view ignores holds, so existing load-only callers are unchanged.
        assert workout_muscle_values(hold) == {}
        assert workout_muscle_values(lift)["pectoralis_major"] == pytest.approx(100 * (1 + 5 / 30))
