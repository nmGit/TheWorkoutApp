from datetime import datetime, timezone

from sqlalchemy import event

from app.extensions import db
from app.models.constants import WEIGHT_UNITS
from app.models.exercise_reference import ExerciseReferenceMixin


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


class WorkoutExercise(ExerciseReferenceMixin, db.Model):
    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(
        db.Integer, db.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False
    )
    # exercise_id / custom_exercise_id / .exercise: see ExerciseReferenceMixin.
    position = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    # Exercises sharing a non-null value, contiguous by position, are a superset -- done back to
    # back as one round, with the same set count forced across every member. Scoped to this
    # workout only (not a cross-workout id); see services/supersets.py.
    superset_group = db.Column(db.Integer, nullable=True)

    workout = db.relationship("Workout", back_populates="exercises")
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

    # This set's real load, in `weight_unit` -- the same as `weight` for a weight_reps exercise,
    # but body weight (the nearest logged BodyweightEntry on or before this set's workout) plus
    # `weight` (the *added* load, normally 0) for a bodyweight_reps one, since `weight` alone is
    # only the added part there, not the exercise's real load. Null exactly when `weight` is
    # (nothing entered yet), or -- bodyweight_reps only -- when body weight has never been
    # logged at all. A stored column, not computed on read: kept in sync automatically
    # (`_recompute_effective_weight` below, on every insert/update, regardless of which code
    # path wrote `weight`) rather than recomputed every time something needs it, and frozen at
    # write time the same way `weight`/`reps` themselves are -- a later edit or backfill to the
    # body-weight log doesn't retroactively change an already-logged set's effective_weight.
    #
    # This is the one place this app's notion of "this set's weight" accounts for body weight;
    # almost everything that means "how much was actually lifted" -- estimated 1RM, volume,
    # PRs, progress charts, progressive overload, per-muscle strength scoring -- reads this
    # instead of `weight` directly, so a bodyweight exercise's numbers aren't always close to
    # zero just because its added weight usually is. See docs/source/data_model.rst.
    effective_weight = db.Column(db.Numeric(8, 4), nullable=True)

    workout_exercise = db.relationship("WorkoutExercise", back_populates="sets")

    def estimated_one_rm(self):
        """Estimated one-rep max (Epley), in this set's own weight_unit -- see
        effective_weight for how a bodyweight_reps set's load is computed."""
        if self.effective_weight is None or self.reps is None or self.reps < 1 or self.is_warmup:
            return None
        weight = float(self.effective_weight)
        if self.reps == 1:
            return weight
        return weight * (1 + self.reps / 30.0)

    def volume(self):
        if self.effective_weight is None or self.reps is None:
            return None
        return float(self.effective_weight) * self.reps


def _compute_effective_weight(target: WorkoutSet):
    """See WorkoutSet.effective_weight. Looks up the owning WorkoutExercise/Workout directly
    (``db.session.get``) rather than through the ``workout_exercise`` relationship, since this
    runs at flush time on a set that may have just been constructed with only
    ``workout_exercise_id`` set -- the relationship itself isn't guaranteed loaded yet, but the
    id always is (it's a required column)."""
    if target.weight is None:
        return None
    weight = float(target.weight)
    we = db.session.get(WorkoutExercise, target.workout_exercise_id)
    exercise = we.exercise if we else None
    if exercise is not None and exercise.tracking_type == "bodyweight_reps":
        # Local imports: services/strength.py imports this module at module load, so importing
        # it back at module scope here would be circular.
        from app.services.strength import body_weight_kg_on
        from app.services.units import convert_weight

        when = we.workout.started_at if we and we.workout else None
        body_kg = body_weight_kg_on(when) if when is not None else None
        if body_kg is None:
            return None
        added_kg = convert_weight(weight, target.weight_unit, "kg")
        weight = convert_weight(body_kg + added_kg, "kg", target.weight_unit)
    return weight


@event.listens_for(WorkoutSet, "before_insert")
@event.listens_for(WorkoutSet, "before_update")
def _set_effective_weight(mapper, connection, target: WorkoutSet):
    """Keeps WorkoutSet.effective_weight in sync with `weight` on every write, from any code
    path (a route, a script, a test fixture, ...) -- a single source of truth instead of every
    writer having to remember to compute it themselves, which is exactly the class of mistake
    (one call site quietly skipped) this project has hit more than once with similar
    "derived field must be kept in sync by hand" designs. Runs unconditionally on every
    update, not just ones that touch `weight` -- simpler and, at this app's data volumes,
    cheap enough not to matter."""
    target.effective_weight = _compute_effective_weight(target)
