from app.extensions import db


class CatalogExerciseNote(db.Model):
    """A user's own note about a catalog exercise (e.g. "stay at 60 until my form is good").

    User data, even though it's about a catalog exercise -- a note is this user's personal
    training commentary, not a correction to the shared exercise itself, so it can't live on
    ExerciseTemplate (the catalog, shared by every user) the way it used to when there was only
    one database. See docs/data_model.rst "Database split". One row per noted exercise; a
    blank note deletes the row rather than storing an empty string (see routes/exercise_
    templates.py's PATCH handler).
    """

    __tablename__ = "catalog_exercise_notes"

    # References catalog.exercise_templates.id -- not a db.ForeignKey: that table lives in a
    # different database file, which SQLite can't enforce a constraint across.
    exercise_id = db.Column(db.Integer, primary_key=True)
    notes = db.Column(db.Text, nullable=False)
