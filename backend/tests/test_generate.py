from datetime import date, datetime, timedelta

from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.generate import plan


def _session(ex, days_ago):
    started = datetime.now() - timedelta(days=days_ago)
    w = Workout(name=f"{ex.name} {days_ago}", started_at=started, completed_at=started + timedelta(hours=1))
    db.session.add(w)
    db.session.flush()
    we = WorkoutExercise(workout_id=w.id, exercise_id=ex.id, position=0)
    db.session.add(we)
    db.session.flush()
    db.session.add(WorkoutSet(workout_exercise_id=we.id, position=0, weight=50, weight_unit="kg", reps=8, completed=True))
    db.session.flush()


def test_legacy_muscle_names_count_as_the_same_muscle():
    from app.serializers import canonical_muscle_slug

    assert canonical_muscle_slug("quads") == "quadriceps"
    assert canonical_muscle_slug("lats") == "latissimus_dorsi"
    assert canonical_muscle_slug("abdominals") == "rectus_abdominis"


def test_second_pick_works_the_next_overdue_muscle(app):
    """Chest last trained 8 days ago, lats 6 days ago. Bench press should come first, then a
    lat exercise, rather than two chest exercises."""
    with app.app_context():
        chest = MuscleGroup(name="Chest", display_order=1)
        back = MuscleGroup(name="Back", display_order=2)
        db.session.add_all([chest, back])
        db.session.flush()
        bench = ExerciseTemplate(name="bench", muscle_group_id=chest.id, tracking_type="weight_reps",
                                 primary_muscles=["pectoralis_major"], secondary_muscles=["triceps_brachii"], is_custom=False)
        pulldown = ExerciseTemplate(name="pulldown", muscle_group_id=back.id, tracking_type="weight_reps",
                                    primary_muscles=["latissimus_dorsi"], secondary_muscles=[], is_custom=False)
        db.session.add_all([bench, pulldown])
        db.session.flush()
        _session(bench, 8)
        _session(pulldown, 6)
        db.session.commit()

        chosen = plan(2, stretching=False, cardio=False, today=date.today())
        assert [e.name for e in chosen] == ["bench", "pulldown"]


def test_with_no_history_the_plan_falls_back_to_all_exercises(app):
    """A new account has no familiar exercises yet, so the plan draws from everything."""
    with app.app_context():
        chest = MuscleGroup(name="Chest", display_order=1)
        db.session.add(chest)
        db.session.flush()
        db.session.add(ExerciseTemplate(name="new fly", muscle_group_id=chest.id, tracking_type="weight_reps",
                                        primary_muscles=["pectoralis_major"], secondary_muscles=[], is_custom=True))
        db.session.commit()
        assert [e.name for e in plan(3, stretching=False, cardio=False, today=date.today())] == ["new fly"]


def test_generate_endpoint_creates_an_active_workout_and_refuses_a_second(client, app):
    with app.app_context():
        back = MuscleGroup(name="Back", display_order=2)
        db.session.add(back)
        db.session.flush()
        pulldown = ExerciseTemplate(name="pulldown", muscle_group_id=back.id, tracking_type="weight_reps",
                                    primary_muscles=["latissimus_dorsi"], secondary_muscles=[], is_custom=False)
        db.session.add(pulldown)
        db.session.flush()
        _session(pulldown, 3)
        db.session.commit()

    first = client.post("/api/workouts/generated", json={"count": 1})
    assert first.status_code == 201
    assert [e["exercise_name"] for e in first.get_json()["exercises"]] == ["pulldown"]
    assert client.post("/api/workouts/generated", json={"count": 1}).status_code == 409
    assert client.post("/api/workouts/generated", json={"count": 0}).status_code == 400


def test_familiar_first_uses_known_exercises_before_unfamiliar_ones(app):
    """A familiar pulldown and an unfamiliar chin-up that works a muscle never trained. The
    never-trained muscle doesn't count, so the pulldown is the only one with a priority."""
    with app.app_context():
        back = MuscleGroup(name="Back", display_order=2)
        db.session.add(back)
        db.session.flush()
        pulldown = ExerciseTemplate(name="pulldown", muscle_group_id=back.id, tracking_type="weight_reps",
                                    primary_muscles=["latissimus_dorsi"], secondary_muscles=[], is_custom=False)
        chin = ExerciseTemplate(name="chin-up", muscle_group_id=back.id, tracking_type="weight_reps",
                                primary_muscles=["rhomboids"], secondary_muscles=[], is_custom=False)
        db.session.add_all([pulldown, chin])
        db.session.flush()
        _session(pulldown, 6)
        db.session.commit()

        # Muscles never trained are ignored, so only the pulldown has a priority.
        assert [e.name for e in plan(1, False, False, date.today(), familiar_first=True)] == ["pulldown"]
        assert [e.name for e in plan(1, False, False, date.today(), familiar_first=False)] == ["pulldown"]
        # The chin-up is still used once the pulldown is taken, so a request for two gets two.
        assert [e.name for e in plan(2, False, False, date.today(), familiar_first=True)] == ["pulldown", "chin-up"]


def test_bodyweight_and_timed_strength_work_is_eligible(app):
    """A bodyweight exercise for an overdue muscle can be chosen, and timed core work too."""
    with app.app_context():
        core = MuscleGroup(name="Core", display_order=5)
        db.session.add(core)
        db.session.flush()
        crunch = ExerciseTemplate(name="bicycle crunch", muscle_group_id=core.id, tracking_type="bodyweight_reps",
                                  primary_muscles=["obliques"], secondary_muscles=[], is_custom=False)
        plank = ExerciseTemplate(name="side plank", muscle_group_id=core.id, tracking_type="time",
                                 primary_muscles=["obliques"], secondary_muscles=[], is_custom=False)
        db.session.add_all([crunch, plank])
        db.session.flush()
        _session(crunch, 10)
        _session(plank, 10)
        db.session.commit()
        names = [e.name for e in plan(1, False, False, date.today())]
        assert names in (["bicycle crunch"], ["side plank"])


def test_a_session_uses_the_two_groups_with_the_most_in_need_muscles(app):
    """Chest (pectorals 8 days) and back (lats 9 days) each have an in-need muscle; legs (1 day)
    has none. A two-exercise session is chest and back. Legs only comes in for a third exercise."""
    with app.app_context():
        chest = MuscleGroup(name="Chest", display_order=1)
        back = MuscleGroup(name="Back", display_order=2)
        legs = MuscleGroup(name="Legs", display_order=5)
        db.session.add_all([chest, back, legs])
        db.session.flush()
        bench = ExerciseTemplate(name="bench", muscle_group_id=chest.id, tracking_type="weight_reps",
                                 primary_muscles=["pectoralis_major"], secondary_muscles=[], is_custom=False)
        pulldown = ExerciseTemplate(name="pulldown", muscle_group_id=back.id, tracking_type="weight_reps",
                                    primary_muscles=["latissimus_dorsi"], secondary_muscles=[], is_custom=False)
        squat = ExerciseTemplate(name="squat", muscle_group_id=legs.id, tracking_type="weight_reps",
                                 primary_muscles=["quadriceps"], secondary_muscles=[], is_custom=False)
        db.session.add_all([bench, pulldown, squat])
        db.session.flush()
        _session(bench, 8)
        _session(pulldown, 9)
        _session(squat, 1)
        db.session.commit()

        two = [e.name for e in plan(2, False, False, date.today(), familiar_first=True)]
        assert sorted(two) == ["bench", "pulldown"]
        three = [e.name for e in plan(3, False, False, date.today(), familiar_first=True)]
        assert "squat" in three


def test_generated_workout_is_named_after_its_groups(app):
    from app.services.generate import workout_name

    with app.app_context():
        chest = MuscleGroup(name="Chest", display_order=1)
        legs = MuscleGroup(name="Legs", display_order=5)
        db.session.add_all([chest, legs])
        db.session.flush()
        bench = ExerciseTemplate(name="bench", muscle_group_id=chest.id, tracking_type="weight_reps",
                                 primary_muscles=["pectoralis_major"], secondary_muscles=[], is_custom=False)
        squat = ExerciseTemplate(name="squat", muscle_group_id=legs.id, tracking_type="weight_reps",
                                 primary_muscles=["quadriceps"], secondary_muscles=[], is_custom=False)
        db.session.add_all([bench, squat])
        db.session.flush()
        assert workout_name([bench, squat]) == "Chest & Legs"
        assert workout_name([bench]) == "Chest"
        assert workout_name([]) == "Generated workout"


def test_chosen_groups_limit_the_session(app):
    """With chest and legs chosen, a session never reaches for back, however overdue it is."""
    with app.app_context():
        chest = MuscleGroup(name="Chest", display_order=1)
        back = MuscleGroup(name="Back", display_order=2)
        legs = MuscleGroup(name="Legs", display_order=5)
        db.session.add_all([chest, back, legs])
        db.session.flush()
        bench = ExerciseTemplate(name="bench", muscle_group_id=chest.id, tracking_type="weight_reps",
                                 primary_muscles=["pectoralis_major"], secondary_muscles=[], is_custom=False)
        pulldown = ExerciseTemplate(name="pulldown", muscle_group_id=back.id, tracking_type="weight_reps",
                                    primary_muscles=["latissimus_dorsi"], secondary_muscles=[], is_custom=False)
        squat = ExerciseTemplate(name="squat", muscle_group_id=legs.id, tracking_type="weight_reps",
                                 primary_muscles=["quadriceps"], secondary_muscles=[], is_custom=False)
        db.session.add_all([bench, pulldown, squat])
        db.session.flush()
        _session(bench, 9)
        _session(pulldown, 20)
        _session(squat, 9)
        db.session.commit()

        names = [e.name for e in plan(3, False, False, date.today(), groups=["Chest", "Legs"])]
        assert "pulldown" not in names
        assert sorted(names) == ["bench", "squat"]
