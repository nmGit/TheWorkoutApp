from datetime import datetime, timezone

from app.extensions import db


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


class TemplateExercise(db.Model):
    __tablename__ = "template_exercises"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("workout_templates.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise_templates.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    target_sets = db.Column(db.Integer, nullable=True)
    target_reps = db.Column(db.String(32), nullable=True)
    target_weight = db.Column(db.Numeric(8, 4), nullable=True)

    template = db.relationship("WorkoutTemplate", back_populates="exercises")
    exercise = db.relationship("ExerciseTemplate")
