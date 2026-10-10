from app.extensions import db

PRIMARY = "primary"
SECONDARY = "secondary"


class Muscle(db.Model):
    """One specific muscle. Each muscle has exactly one row, identified by its slug, so the
    same muscle can't be stored under two names. Body regions are not muscles and aren't stored."""

    __tablename__ = "muscles"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)


class ExerciseMuscle(db.Model):
    """A muscle an exercise works, and whether it's primary or secondary for that exercise."""

    __tablename__ = "exercise_muscles"

    exercise_id = db.Column(
        db.Integer, db.ForeignKey("exercise_templates.id", ondelete="CASCADE"), primary_key=True
    )
    muscle_id = db.Column(db.Integer, db.ForeignKey("muscles.id"), primary_key=True)
    role = db.Column(db.String(16), nullable=False)

    exercise = db.relationship("ExerciseTemplate", back_populates="muscle_links")
    muscle = db.relationship("Muscle", lazy="joined")
