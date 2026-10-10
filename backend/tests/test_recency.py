from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet


def test_muscle_recency_counts_completed_working_sets_only(client, app):
    today = datetime.now(timezone.utc)
    with app.app_context():
        legs = MuscleGroup(name="Legs", display_order=5)
        chest = MuscleGroup(name="Chest", display_order=1)
        cardio = MuscleGroup(name="Cardio", display_order=7)
        db.session.add_all([legs, chest, cardio])
        db.session.flush()
        squat = ExerciseTemplate(name="squat", muscle_group_id=legs.id, tracking_type="weight_reps", primary_muscles=["quadriceps"], is_custom=False)
        bench = ExerciseTemplate(name="bench", muscle_group_id=chest.id, tracking_type="weight_reps", primary_muscles=["pectoralis_major"], is_custom=False)
        run = ExerciseTemplate(name="run", muscle_group_id=cardio.id, tracking_type="cardio", primary_muscles=[], is_custom=False)
        db.session.add_all([squat, bench, run])
        db.session.flush()

        def session(ex, days_ago, **set_fields):
            started = today - timedelta(days=days_ago)
            w = Workout(name="w", started_at=started, completed_at=started + timedelta(hours=1))
            db.session.add(w)
            db.session.flush()
            we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, position=0)
            db.session.add(we)
            db.session.flush()
            db.session.add(WorkoutSet(workout_exercise_id=we.id, position=0, weight=100, weight_unit="kg", reps=5, completed=True, **set_fields))
            db.session.flush()

        session(squat, 2)
        session(squat, 9, is_warmup=True)  # warm-ups don't count
        session(bench, 0, is_dropset=True)  # drop sets don't count
        session(run, 1)  # cardio is not a training group
        db.session.commit()

    body = client.get("/api/muscles/recency").get_json()["muscles"]
    assert body["quadriceps"]["days_since"] == 2
    # Warm-ups and drop sets don't count, so the bench press never trained the chest.
    assert "pectoralis_major" not in body
    # Cardio doesn't work a muscle that's listed, so it doesn't appear.
    assert len(body) == 1
