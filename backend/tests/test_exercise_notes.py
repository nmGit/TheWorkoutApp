from datetime import datetime

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise


def _instance(client, app):
    with app.app_context():
        ex = ExerciseTemplate(name="plank", tracking_type="time", primary_muscles=["abs"], is_custom=True)
        db.session.add(ex)
        db.session.flush()
        workout = Workout(name="core", started_at=datetime(2026, 1, 5, 9), completed_at=None)
        db.session.add(workout)
        db.session.flush()
        we = WorkoutExercise(workout_id=workout.id, exercise_id=ex.id, position=0)
        db.session.add(we)
        db.session.commit()
        return workout.id, we.id, ex.id


def test_instance_note_is_saved_and_cleared(client, app):
    wid, weid, _ = _instance(client, app)
    body = client.patch(f"/api/workouts/{wid}/exercises/{weid}", json={"notes": "  felt strong  "}).get_json()
    assert body["exercises"][0]["notes"] == "felt strong"
    body = client.patch(f"/api/workouts/{wid}/exercises/{weid}", json={"notes": "  "}).get_json()
    assert body["exercises"][0]["notes"] is None


def test_instance_note_rejects_other_workouts_exercise(client, app):
    wid, weid, _ = _instance(client, app)
    assert client.patch(f"/api/workouts/{wid + 99}/exercises/{weid}", json={"notes": "x"}).status_code == 404


def test_template_note_is_shared_by_the_exercise(client, app):
    _, _, exercise_id = _instance(client, app)
    client.patch(f"/api/exercise-templates/{exercise_id}", json={"notes": "keep hips level"})
    assert client.get(f"/api/exercise-templates/{exercise_id}").get_json()["notes"] == "keep hips level"


def test_muscle_filter_finds_exercises_that_work_the_muscle(client, app):
    with app.app_context():
        from app.models.exercise import MuscleGroup
        from app.models.exercise_template import ExerciseTemplate as ET

        group = MuscleGroup(name="Legs", display_order=5)
        db.session.add(group)
        db.session.flush()
        squat = ET(name="squat", muscle_group_id=group.id, tracking_type="weight_reps",
                   primary_muscles=["quadriceps"], secondary_muscles=["hamstrings"], is_custom=True)
        curl = ET(name="curl", muscle_group_id=group.id, tracking_type="weight_reps",
                  primary_muscles=["biceps_brachii"], secondary_muscles=[], is_custom=True)
        db.session.add_all([squat, curl])
        db.session.commit()

    resp = client.get("/api/exercise-templates?muscle=hamstrings")
    assert resp.status_code == 200
    assert [i["name"] for i in resp.get_json()["items"]] == ["squat"]
    assert client.get("/api/exercise-templates?muscle=nonsense").get_json()["total"] == 0
