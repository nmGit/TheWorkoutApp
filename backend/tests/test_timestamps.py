from app.extensions import db
from app.models.workout import Workout


def test_workout_timestamps_carry_a_utc_offset(client, app):
    # Naive strings read as local time in the browser, which broke the elapsed timer.
    with app.app_context():
        workout = Workout(name="Timer check")
        db.session.add(workout)
        db.session.commit()
        workout_id = workout.id

    body = client.get(f"/api/workouts/{workout_id}").get_json()
    assert body["started_at"].endswith("+00:00")
    assert body["completed_at"] is None
