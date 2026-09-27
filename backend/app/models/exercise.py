from datetime import datetime, timezone

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


def _utcnow():
    return datetime.now(timezone.utc)


class MuscleGroup(db.Model):
    __tablename__ = "muscle_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    exercises = db.relationship(
        "Exercise", back_populates="muscle_group", order_by="Exercise.name"
    )


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    muscle_group_id = db.Column(
        db.Integer, db.ForeignKey("muscle_groups.id"), nullable=False
    )
    equipment = db.Column(
        db.Enum(*EQUIPMENT_TYPES, name="equipment_type", native_enum=False),
        nullable=False,
        default="other",
    )
    tracking_type = db.Column(
        db.Enum(*TRACKING_TYPES, name="tracking_type", native_enum=False),
        nullable=False,
    )
    is_custom = db.Column(db.Boolean, nullable=False, default=True)
    default_rest_seconds = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    muscle_group = db.relationship("MuscleGroup", back_populates="exercises")
    workout_exercises = db.relationship(
        "WorkoutExercise", back_populates="exercise", cascade="none"
    )
    template_exercises = db.relationship(
        "TemplateExercise", back_populates="exercise", cascade="none"
    )

    __table_args__ = (
        db.UniqueConstraint("name", "muscle_group_id", name="uq_exercise_name_group"),
    )

    def has_logged_sets(self) -> bool:
        from app.models.workout import WorkoutSet, WorkoutExercise

        return (
            db.session.query(WorkoutSet.id)
            .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .filter(WorkoutExercise.exercise_id == self.id)
            .first()
            is not None
        )
