from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.models.template import TemplateExercise, WorkoutTemplate


def test_template_muscles_summarise_its_exercises(client, app):
    with app.app_context():
        legs = MuscleGroup(name="Legs", display_order=5)
        chest = MuscleGroup(name="Chest", display_order=1)
        db.session.add_all([legs, chest])
        db.session.flush()
        squat = ExerciseTemplate(
            name="squat", muscle_group_id=legs.id,
            primary_muscles=["quadriceps", "gluteus_maximus"],
            secondary_muscles=["hamstrings"], is_custom=False,
        )
        # Legacy spelling of the same muscle as the squat's, so it must appear once.
        press = ExerciseTemplate(
            name="press", muscle_group_id=chest.id,
            primary_muscles=["pectorals"], secondary_muscles=["quadriceps"], is_custom=False,
        )
        db.session.add_all([squat, press])
        db.session.flush()
        template = WorkoutTemplate(name="Mixed day")
        db.session.add(template)
        db.session.flush()
        db.session.add_all([
            TemplateExercise(template_id=template.id, exercise_id=squat.id, position=0),
            TemplateExercise(template_id=template.id, exercise_id=press.id, position=1),
        ])
        db.session.commit()
        template_id = template.id

    body = client.get(f"/api/templates/{template_id}").get_json()
    assert body["muscles"] == {
        "primary": ["gluteus_maximus", "pectoralis_major", "quadriceps"],
        # quadriceps is primary for the squat, so it isn't repeated as secondary.
        "secondary": ["hamstrings"],
        # Chest comes before Legs by display order, not alphabetically.
        "groups": ["Chest", "Legs"],
    }
