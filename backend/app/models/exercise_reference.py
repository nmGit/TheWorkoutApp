"""Shared by WorkoutExercise and TemplateExercise: an exercise "slot" references either a
catalog exercise (ExerciseTemplate, the shared database) or the user's own custom one
(CustomExerciseTemplate, this user's database) -- never both, never neither. The two tables
live in separate SQLite files (see docs/data_model.rst "Database split"), so there's no single
foreign key that can point at either one; exactly one of exercise_id/custom_exercise_id is set,
enforced by a CHECK constraint rather than a shared column.
"""

from sqlalchemy.orm import declared_attr

from app.extensions import db


class ExerciseReferenceMixin:
    @declared_attr
    def exercise_id(cls):
        # References catalog.exercise_templates.id -- not a db.ForeignKey: that table lives in
        # a different database file, which SQLite can't enforce a constraint across.
        return db.Column(db.Integer, nullable=True)

    @declared_attr
    def custom_exercise_id(cls):
        # Same database as this table, so this one is a real, enforced foreign key.
        return db.Column(db.Integer, db.ForeignKey("custom_exercise_templates.id"), nullable=True)

    @declared_attr
    def custom_exercise(cls):
        return db.relationship("CustomExerciseTemplate")

    @declared_attr
    def __table_args__(cls):
        return (
            db.CheckConstraint(
                "(exercise_id IS NULL) != (custom_exercise_id IS NULL)",
                name=f"ck_{cls.__tablename__}_exactly_one_exercise",
            ),
        )

    @property
    def exercise_ref(self) -> tuple[str, int]:
        """A collision-free identity for whichever exercise this slot points to -- plain
        ``exercise_id`` alone isn't unique across the split (a catalog exercise and a custom one
        can share the same id, since each table has its own independent sequence), so anything
        that needs to group/compare "the same exercise" across rows (per-exercise progression
        history, per-exercise strength baselines, ...) should key on this instead."""
        if self.exercise_id is not None:
            return ("catalog", self.exercise_id)
        return ("custom", self.custom_exercise_id)

    @property
    def exercise(self):
        """Whichever of the two this slot actually points to -- read from whichever database it
        lives in. A catalog lookup isn't an eager-loadable relationship (it can't be, across
        database files), but SQLAlchemy's session identity map means a given exercise id is
        only ever actually fetched once per session regardless of how many slots reference it,
        so this stays cheap for the handful of distinct exercises a real workout/template uses."""
        if self.exercise_id is not None:
            from app.models.exercise_template import ExerciseTemplate

            return db.session.get(ExerciseTemplate, self.exercise_id)
        return self.custom_exercise


def exercise_ref_filter(model, ref: tuple[str, int]):
    """A filter condition on `model` (WorkoutExercise or TemplateExercise) matching the slot(s)
    pointing at `ref` (an (exercise|custom, id) pair -- see exercise_ref above, or
    ExerciseTemplate.ref/CustomExerciseTemplate.ref for a specific exercise row)."""
    kind, id_ = ref
    return model.exercise_id == id_ if kind == "catalog" else model.custom_exercise_id == id_
