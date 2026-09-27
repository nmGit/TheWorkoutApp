from datetime import datetime, timezone

from app.extensions import db
from app.models.constants import WEIGHT_UNITS


def _utcnow():
    return datetime.now(timezone.utc)


class Workout(db.Model):
    __tablename__ = "workouts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, default="Workout")
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    body_weight = db.Column(db.Numeric(8, 4), nullable=True)

    template = db.relationship("WorkoutTemplate", back_populates="workouts")
    exercises = db.relationship(
        "WorkoutExercise",
        back_populates="workout",
        order_by="WorkoutExercise.position",
        cascade="all, delete-orphan",
    )

    @property
    def is_active(self) -> bool:
        return self.completed_at is None


class WorkoutExercise(db.Model):
    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    workout = db.relationship("Workout", back_populates="exercises")
    exercise = db.relationship("Exercise", back_populates="workout_exercises")
    sets = db.relationship(
        "WorkoutSet",
        back_populates="workout_exercise",
        order_by="WorkoutSet.position",
        cascade="all, delete-orphan",
    )


class WorkoutSet(db.Model):
    __tablename__ = "workout_sets"

    id = db.Column(db.Integer, primary_key=True)
    workout_exercise_id = db.Column(
        db.Integer, db.ForeignKey("workout_exercises.id", ondelete="CASCADE"), nullable=False
    )
    position = db.Column(db.Integer, nullable=False, default=0)

    weight = db.Column(db.Numeric(8, 4), nullable=True)
    weight_unit = db.Column(
        db.Enum(*WEIGHT_UNITS, name="set_weight_unit", native_enum=False), nullable=True
    )
    reps = db.Column(db.Integer, nullable=True)
    duration_seconds = db.Column(db.Integer, nullable=True)
    distance_meters = db.Column(db.Numeric(8, 2), nullable=True)

    is_warmup = db.Column(db.Boolean, nullable=False, default=False)
    is_dropset = db.Column(db.Boolean, nullable=False, default=False)
    rpe = db.Column(db.Numeric(3, 1), nullable=True)
    completed = db.Column(db.Boolean, nullable=False, default=True)

    workout_exercise = db.relationship("WorkoutExercise", back_populates="sets")

    def estimated_one_rm(self):
        if self.weight is None or self.reps is None or self.reps < 1 or self.is_warmup:
            return None
        weight = float(self.weight)
        if self.reps == 1:
            return weight
        return weight * (1 + self.reps / 30.0)

    def volume(self):
        if self.weight is None or self.reps is None:
            return None
        return float(self.weight) * self.reps
