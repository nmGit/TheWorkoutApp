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
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise_templates.id"), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    # Exercises sharing a non-null value, contiguous by position, are a superset -- done back to
    # back as one round, with the same set count forced across every member. Scoped to this
    # workout only (not a cross-workout id); see services/supersets.py.
    superset_group = db.Column(db.Integer, nullable=True)

    workout = db.relationship("Workout", back_populates="exercises")
    exercise = db.relationship("ExerciseTemplate")
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
    rest_seconds = db.Column(db.Integer, nullable=True)
    # What a set started from a template is expected to be. Shown as ghost text until the set is
    # completed; completing the set copies these into the entered fields above.
    planned_weight = db.Column(db.Numeric(8, 4), nullable=True)
    planned_weight_unit = db.Column(db.String(3), nullable=True)
    planned_reps = db.Column(db.Integer, nullable=True)
    planned_duration_seconds = db.Column(db.Integer, nullable=True)
    # True when the planned values above are actually different from what progressive overload
    # is comparing them against (the "anchor": last session's best set) -- a real increase, not
    # just progression having run. Cleared along with the planned_* fields when the set is
    # completed.
    planned_is_progressed = db.Column(db.Boolean, nullable=False, default=False)
    # True whenever progressive overload actually ran for this set (there was a previous
    # session to progress from, and progression isn't off in Settings), whether or not it
    # changed anything -- a plain copy (warm-ups/drops, or no history/progression off) is
    # always False here. planned_is_progressed implies this; this doesn't imply
    # planned_is_progressed (progression can run and still land on the same value as last
    # time -- see services/sets_plan.progress_working). Cleared along with the planned_* fields
    # when the set is completed, same as planned_is_progressed.
    planned_progression_active = db.Column(db.Boolean, nullable=False, default=False)

    is_warmup = db.Column(db.Boolean, nullable=False, default=False)
    is_dropset = db.Column(db.Boolean, nullable=False, default=False)
    rpe = db.Column(db.Numeric(3, 1), nullable=True)
    completed = db.Column(db.Boolean, nullable=False, default=True)

    workout_exercise = db.relationship("WorkoutExercise", back_populates="sets")

    def estimated_one_rm(self):
        """Estimated one-rep max (Epley), in this set's own weight_unit.

        For a bodyweight_reps exercise, the set's own `weight` is only the *added* load (a
        weighted vest, normally 0) -- the real load is body weight too, so it's added on top
        (nearest logged BodyweightEntry on or before this set's workout; see
        services/strength.body_weight_kg_on). None if body weight has never been logged at
        all, same as any other missing input here.
        """
        if self.weight is None or self.reps is None or self.reps < 1 or self.is_warmup:
            return None
        weight = float(self.weight)
        exercise = self.workout_exercise.exercise if self.workout_exercise else None
        if exercise is not None and exercise.tracking_type == "bodyweight_reps":
            # Local imports: services/strength.py imports this module's Workout/WorkoutExercise
            # at module load, so importing it back at module scope here would be circular.
            from app.services.strength import body_weight_kg_on
            from app.services.units import convert_weight

            body_kg = body_weight_kg_on(self.workout_exercise.workout.started_at)
            if body_kg is None:
                return None
            added_kg = convert_weight(weight, self.weight_unit, "kg")
            weight = convert_weight(body_kg + added_kg, "kg", self.weight_unit)
        if self.reps == 1:
            return weight
        return weight * (1 + self.reps / 30.0)

    def volume(self):
        if self.weight is None or self.reps is None:
            return None
        return float(self.weight) * self.reps
