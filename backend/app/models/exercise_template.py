from datetime import datetime, timezone

from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class ExerciseTemplate(db.Model):
    """A reusable exercise blueprint.

    Templates are either sourced from the bundled exercises-dataset
    submodule (external_id set, is_custom False) or authored by a user as a
    custom exercise (external_id null, is_custom True). An `Exercise` row
    created from a template links back here via `Exercise.template_id`,
    which is how the exercise detail view surfaces the template's image and
    English step-by-step instructions.
    """

    __tablename__ = "exercise_templates"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(16), unique=True, nullable=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=True)
    body_part = db.Column(db.String(64), nullable=True)
    equipment = db.Column(db.String(64), nullable=True)
    target_muscle = db.Column(db.String(64), nullable=True)
    muscle_group = db.Column(db.String(64), nullable=True)
    secondary_muscles = db.Column(db.JSON, nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    instruction_steps = db.Column(db.JSON, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    attribution = db.Column(db.String(255), nullable=True)
    is_custom = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    exercises = db.relationship("Exercise", back_populates="template", cascade="none")
