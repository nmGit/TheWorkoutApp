from datetime import datetime, timezone

from app.extensions import db
from app.models.exercise import TRACKING_TYPES


def _utcnow():
    return datetime.now(timezone.utc)


class ExerciseTemplate(db.Model):
    """An exercise, the abstract idea of it: name, muscle group, equipment,
    tracking type, description/instructions/notes. This is what a workout's
    logged sets (`WorkoutExercise`/`WorkoutSet`) and a saved routine's slots
    (`TemplateExercise`) link back to -- there is no separate per-user
    "Exercise" row anymore (see docs/source/review.rst for why that split
    was removed: it let two different exercises collide onto one template).

    Templates are either sourced from a bundled dataset (`is_custom` False)
    or authored by a user from scratch (`is_custom` True). There are two
    dataset sources, both git submodules: the original exercises-dataset
    (`external_id`, `image_path`, ...) and RepDB (`repdb_id`, `repdb_images`,
    `tips`, ...). One template can carry both -- RepDB's images/text/muscles
    are preferred wherever present, the original's stay as the fallback, and
    each source's own fields are stored as that source provides them. The
    user-editable fields (`name`, `equipment`, `tracking_type`,
    `muscle_group_id`, `notes`, `is_custom`) are owned by the app: seeding
    sets them only when it first creates a row, never on a re-run. `equipment` is this
    app's own fixed vocabulary (`EQUIPMENT_TYPES`), used for filtering;
    `equipment_raw` preserves the dataset's own original wording, which
    doesn't share that vocabulary, purely for display/reference.
    `muscle_group_id` is this app's own fixed `MuscleGroup` list -- the
    dataset's own classification stays on `body_part`/`category`/
    `muscle_group` (plain text, dataset-only, never used for filtering).
    """

    __tablename__ = "exercise_templates"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(16), unique=True, nullable=True)
    name = db.Column(db.String(128), nullable=False)
    category = db.Column(db.String(64), nullable=True)
    body_part = db.Column(db.String(64), nullable=True)
    # Plain string, not an Enum column, on purpose: this column briefly
    # holds the dataset's raw equipment wording (e.g. "stepmill machine")
    # for every pre-existing row until the one-time merge migration
    # (scripts/merge_exercises_into_templates.py) rewrites it to one of
    # EQUIPMENT_TYPES -- an Enum column validates values coming *from* the
    # database too, so it would reject reading those transitional rows.
    # EQUIPMENT_TYPES membership is still enforced at the API layer (see
    # app/routes/exercise_templates.py) for every write going forward.
    equipment = db.Column(db.String(64), nullable=True)
    equipment_raw = db.Column(db.String(64), nullable=True)
    target_muscle = db.Column(db.String(64), nullable=True)
    muscle_group = db.Column(db.String(64), nullable=True)
    muscle_group_id = db.Column(db.Integer, db.ForeignKey("muscle_groups.id"), nullable=True)
    tracking_type = db.Column(
        db.Enum(*TRACKING_TYPES, name="tracking_type", native_enum=False), nullable=True
    )
    # Muscles worked, as the source dataset provides them (RepDB: anatomical
    # slugs like "pectoralis_major"; the original dataset: its own terms like
    # "pectorals"). Not translated between vocabularies.
    primary_muscles = db.Column(db.JSON, nullable=True)
    secondary_muscles = db.Column(db.JSON, nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    instruction_steps = db.Column(db.JSON, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    attribution = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_custom = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    # RepDB-sourced fields (https://repdb.co, external/repdb-exercise-dataset).
    repdb_id = db.Column(db.String(64), nullable=True)
    repdb_images = db.Column(db.JSON, nullable=True)  # 1-2 repo-relative paths (start/peak, or one)
    tips = db.Column(db.JSON, nullable=True)
    difficulty = db.Column(db.String(16), nullable=True)
    mechanic = db.Column(db.String(16), nullable=True)

    # Other names this exercise is known by (e.g. the Strong app's wording
    # for an exercise that was merged into this one); consulted when
    # importing so a merged-away name still resolves.
    aliases = db.Column(db.JSON, nullable=True)

    __table_args__ = (db.Index("uq_exercise_templates_repdb_id", "repdb_id", unique=True),)

    app_muscle_group = db.relationship("MuscleGroup", back_populates="exercise_templates")

    def has_logged_sets(self) -> bool:
        from app.models.workout import WorkoutExercise, WorkoutSet

        return (
            db.session.query(WorkoutSet.id)
            .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .filter(WorkoutExercise.exercise_id == self.id)
            .first()
            is not None
        )
