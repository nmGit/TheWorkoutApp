from app.extensions import db

EQUIPMENT_TYPES = (
    "barbell",
    "dumbbell",
    "machine",
    "cable",
    "bodyweight",
    "kettlebell",
    "other",
)

TRACKING_TYPES = ("weight_reps", "bodyweight_reps", "time", "cardio")


class MuscleGroup(db.Model):
    # Shared catalog reference data (the app's own fixed vocabulary, used by both dataset and
    # custom exercises) -- see docs/data_model.rst "Database split".
    __bind_key__ = "catalog"
    __tablename__ = "muscle_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    exercise_templates = db.relationship(
        "ExerciseTemplate", back_populates="app_muscle_group", order_by="ExerciseTemplate.name"
    )
