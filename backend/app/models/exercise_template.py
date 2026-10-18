from datetime import datetime, timezone

from app.extensions import db
from app.models.exercise import TRACKING_TYPES
from app.models.muscle import PRIMARY, SECONDARY


def _utcnow():
    return datetime.now(timezone.utc)


class ExerciseTemplate(db.Model):
    """A catalog exercise: name, muscle group, equipment, tracking type,
    description/instructions/notes, sourced from a bundled dataset -- never
    user-authored (see `CustomExerciseTemplate` for that). This is what a
    workout's logged sets (`WorkoutExercise`/`WorkoutSet`) and a saved
    routine's slots (`TemplateExercise`) can link back to, via their
    `exercise_id`; a `custom_exercise_id` on those same rows links to a
    `CustomExerciseTemplate` instead -- exactly one of the two is ever set,
    since the two live in separate databases (see docs/data_model.rst
    "Database split") and a single column can't point at either.

    Catalog (shared) data: lives in its own database (the `"catalog"` bind),
    common to every user, rebuilt from the bundled datasets by
    `scripts/seed_exercise_templates.py` rather than hand-migrated. There are
    two dataset sources, both git submodules: the original exercises-dataset
    (`external_id`, `image_path`, ...) and RepDB (`repdb_id`, `repdb_images`,
    `tips`, ...). One template can carry both -- RepDB's images/text/muscles
    are preferred wherever present, the original's stay as the fallback, and
    each source's own fields are stored as that source provides them. The
    user-editable fields (`name`, `equipment`, `tracking_type`,
    `muscle_group_id`, `notes`) are owned by the app: seeding sets them only
    when it first creates a row, never on a re-run. `equipment` is this
    app's own fixed vocabulary (`EQUIPMENT_TYPES`), used for filtering;
    `equipment_raw` preserves the dataset's own original wording, which
    doesn't share that vocabulary, purely for display/reference.
    `muscle_group_id` is this app's own fixed `MuscleGroup` list -- the
    dataset's own classification stays on `body_part`/`category`/
    `muscle_group` (plain text, dataset-only, never used for filtering).
    """

    __bind_key__ = "catalog"
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
    # The muscles this exercise works, as links to the `muscles` table (see models/muscle.py).
    muscle_links = db.relationship(
        "ExerciseMuscle", back_populates="exercise", cascade="all, delete-orphan"
    )
    instructions = db.Column(db.Text, nullable=True)
    instruction_steps = db.Column(db.JSON, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    attribution = db.Column(db.String(255), nullable=True)
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

    @property
    def is_custom(self) -> bool:
        """Always False here -- a custom exercise is a CustomExerciseTemplate instead, never a
        row in this table. Kept as a property (not a stored column) so code that checks
        `exercise.is_custom` works the same regardless of which of the two it actually got,
        without an isinstance check at every call site."""
        return False

    @property
    def ref(self) -> tuple[str, int]:
        """See ExerciseReferenceMixin.exercise_ref -- the same collision-free identity, from the
        exercise's own side rather than a WorkoutExercise/TemplateExercise row's."""
        return ("catalog", self.id)

    @property
    def notes(self) -> str | None:
        """This user's own note about this catalog exercise -- see CatalogExerciseNote (user
        data, in the other database, since a note is personal commentary, not a correction to
        the shared exercise itself)."""
        from app.models.catalog_exercise_note import CatalogExerciseNote

        row = db.session.get(CatalogExerciseNote, self.id)
        return row.notes if row else None

    @notes.setter
    def notes(self, value: str | None) -> None:
        from app.models.catalog_exercise_note import CatalogExerciseNote

        value = (value or "").strip() or None
        row = db.session.get(CatalogExerciseNote, self.id)
        if value is None:
            if row is not None:
                db.session.delete(row)
            return
        if row is None:
            db.session.add(CatalogExerciseNote(exercise_id=self.id, notes=value))
        else:
            row.notes = value

    @property
    def is_stretch(self) -> bool:
        """A stretch or mobility movement. It isn't strength work, so it never counts toward
        a muscle's strength, its recency, or what a generated workout trains."""
        group = self.app_muscle_group.name if self.app_muscle_group else None
        return self.category == "stretching" or group == "Mobility"

    # The names the rest of the app uses for an exercise's muscles: canonical slugs, read from
    # the links. Writing names maps them through the muscle catalog, so a dataset name for a
    # region or an old spelling becomes the specific muscles it means.

    @property
    def primary_muscles(self) -> list[str]:
        return [link.muscle.slug for link in self.muscle_links if link.role == PRIMARY]

    @primary_muscles.setter
    def primary_muscles(self, names) -> None:
        self._set_roles(primary=names)

    @property
    def secondary_muscles(self) -> list[str]:
        return [link.muscle.slug for link in self.muscle_links if link.role == SECONDARY]

    @secondary_muscles.setter
    def secondary_muscles(self, names) -> None:
        self._set_roles(secondary=names)

    def _set_roles(self, primary=None, secondary=None) -> None:
        """Replace the primary or secondary muscles, keeping the other role. A muscle that is
        primary is never also secondary."""
        from app.models.muscle import ExerciseMuscle, Muscle
        from app.services.muscle_catalog import CANONICAL_MUSCLES, resolve

        def slugs(names) -> list[str]:
            found: list[str] = []
            for raw in names or []:
                for slug in resolve(raw):
                    if slug not in found:
                        found.append(slug)
            return found

        roles = {link.muscle.slug: link.role for link in self.muscle_links}
        if primary is not None:
            new = slugs(primary)
            roles = {slug: role for slug, role in roles.items() if role != PRIMARY}
            for slug in new:
                roles[slug] = PRIMARY
        if secondary is not None:
            roles = {slug: role for slug, role in roles.items() if role != SECONDARY}
            for slug in slugs(secondary):
                if roles.get(slug) != PRIMARY:
                    roles[slug] = SECONDARY

        rows = {}
        for slug, role in roles.items():
            muscle = Muscle.query.filter_by(slug=slug).first()
            if muscle is None:
                muscle = Muscle(slug=slug, name=CANONICAL_MUSCLES[slug])
                db.session.add(muscle)
            rows[slug] = ExerciseMuscle(muscle=muscle, role=role)
        self.muscle_links = list(rows.values())

    def has_logged_sets(self) -> bool:
        from app.models.workout import WorkoutExercise, WorkoutSet

        return (
            db.session.query(WorkoutSet.id)
            .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .filter(WorkoutExercise.exercise_id == self.id)
            .first()
            is not None
        )


class CustomExerciseTemplate(db.Model):
    """An exercise a user authored from scratch, as opposed to one sourced from a bundled
    dataset (`ExerciseTemplate`). User data -- lives in the user's own database (the default
    bind), not the shared catalog one, since it belongs to this user alone (see
    docs/data_model.rst "Database split").

    Exposes the same read interface as `ExerciseTemplate` wherever the two are used
    interchangeably (`is_custom`, `is_stretch`, `primary_muscles`/`secondary_muscles`, and every
    field `serialize_exercise_template` reads) so calling code -- the serializer, the strength
    scorer, the exercise picker -- doesn't need to know or care which one it got. Dataset-only
    fields (`external_id`, `instructions`, image paths, ...) simply read back `None`/empty
    rather than existing as real columns, since nothing ever sets them for a custom exercise.

    Muscles are stored directly as canonical slug strings (JSON arrays), not via the `Muscle`/
    `ExerciseMuscle` link tables `ExerciseTemplate` uses -- those live in the catalog database,
    and a slug is already a stable, self-describing identifier that doesn't need a row of its
    own the way the catalog's muscle-name reconciliation does (see `services/muscle_catalog.py`).
    `muscle_group_id` still refers to the catalog's `MuscleGroup` table (the app's one fixed
    list, shared by dataset and custom exercises alike) -- not a database-enforced foreign key,
    since SQLite can't enforce one across two files, but resolved the same way at the app layer.
    """

    __tablename__ = "custom_exercise_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    equipment = db.Column(db.String(64), nullable=True)
    tracking_type = db.Column(
        db.Enum(*TRACKING_TYPES, name="custom_tracking_type", native_enum=False), nullable=True
    )
    # References catalog.muscle_groups.id -- see the class docstring on why this isn't a
    # db.ForeignKey.
    muscle_group_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    _primary_muscles = db.Column("primary_muscles", db.JSON, nullable=True)
    _secondary_muscles = db.Column("secondary_muscles", db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    @property
    def is_custom(self) -> bool:
        return True

    @property
    def ref(self) -> tuple[str, int]:
        return ("custom", self.id)

    @property
    def app_muscle_group(self):
        """The catalog's MuscleGroup this exercise belongs to, resolved with a plain lookup
        rather than a relationship -- MuscleGroup lives in the other database, and a cross-bind
        relationship isn't worth the complexity for the couple of places that need this
        (serialize_exercise_template, is_stretch below)."""
        if self.muscle_group_id is None:
            return None
        from app.models.exercise import MuscleGroup

        return db.session.get(MuscleGroup, self.muscle_group_id)

    @property
    def is_stretch(self) -> bool:
        """Same rule as ExerciseTemplate.is_stretch."""
        group = self.app_muscle_group
        return bool(group and group.name == "Mobility")

    @property
    def primary_muscles(self) -> list[str]:
        return list(self._primary_muscles or [])

    @primary_muscles.setter
    def primary_muscles(self, slugs) -> None:
        self._primary_muscles = list(slugs or [])

    @property
    def secondary_muscles(self) -> list[str]:
        return list(self._secondary_muscles or [])

    @secondary_muscles.setter
    def secondary_muscles(self, slugs) -> None:
        self._secondary_muscles = list(slugs or [])

    # Dataset-only fields ExerciseTemplate has and a custom exercise never does -- stubbed so
    # serialize_exercise_template and image_count (app/serializers.py) work unchanged on either.
    external_id = None
    category = None
    body_part = None
    equipment_raw = None
    target_muscle = None
    muscle_group = None
    instructions = None
    instruction_steps = None
    repdb_images = None
    tips = None
    difficulty = None
    mechanic = None
    image_path = None
    attribution = None

    def has_logged_sets(self) -> bool:
        from app.models.workout import WorkoutExercise, WorkoutSet

        return (
            db.session.query(WorkoutSet.id)
            .join(WorkoutExercise, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .filter(WorkoutExercise.custom_exercise_id == self.id)
            .first()
            is not None
        )
