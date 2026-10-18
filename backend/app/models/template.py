from datetime import datetime, timezone

from app.extensions import db
from app.models.exercise_reference import ExerciseReferenceMixin


def _utcnow():
    return datetime.now(timezone.utc)


class WorkoutTemplate(db.Model):
    __tablename__ = "workout_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    exercises = db.relationship(
        "TemplateExercise",
        back_populates="template",
        order_by="TemplateExercise.position",
        cascade="all, delete-orphan",
    )
    workouts = db.relationship("Workout", back_populates="template")


class TemplateExercise(ExerciseReferenceMixin, db.Model):
    __tablename__ = "template_exercises"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("workout_templates.id", ondelete="CASCADE"), nullable=False
    )
    # exercise_id / custom_exercise_id / .exercise: see ExerciseReferenceMixin.
    position = db.Column(db.Integer, nullable=False, default=0)
    # How many sets of each kind the workout starts with. Weights and reps aren't stored here: they
    # come from the last time this exercise was done.
    target_sets = db.Column(db.Integer, nullable=True)
    warmup_sets = db.Column(db.Integer, nullable=False, default=0)
    drop_sets = db.Column(db.Integer, nullable=False, default=0)
    target_reps = db.Column(db.String(32), nullable=True)
    target_weight = db.Column(db.Numeric(8, 4), nullable=True)
    # Exercises sharing a non-null value, contiguous by position, are a superset -- done back to
    # back as one round, with the same working-set count forced across every member. Scoped to
    # this template only (not a cross-template id); see services/supersets.py.
    superset_group = db.Column(db.Integer, nullable=True)

    template = db.relationship("WorkoutTemplate", back_populates="exercises")
