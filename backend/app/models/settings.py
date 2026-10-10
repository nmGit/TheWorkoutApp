from app.extensions import db
from app.models.constants import DISTANCE_UNITS, EXPERIENCE_LEVELS, PROGRESSION_METHODS, THEMES, WEIGHT_UNITS

SETTINGS_SINGLETON_ID = 1


class UserSettings(db.Model):
    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    weight_unit = db.Column(
        db.Enum(*WEIGHT_UNITS, name="settings_weight_unit", native_enum=False),
        nullable=False,
        default="lbs",
    )
    distance_unit = db.Column(
        db.Enum(*DISTANCE_UNITS, name="settings_distance_unit", native_enum=False),
        nullable=False,
        default="mi",
    )
    default_rest_seconds = db.Column(db.Integer, nullable=False, default=90)
    theme = db.Column(
        db.Enum(*THEMES, name="settings_theme", native_enum=False),
        nullable=False,
        default="system",
    )
    progression_method = db.Column(
        db.Enum(*PROGRESSION_METHODS, name="settings_progression_method", native_enum=False),
        nullable=False,
        default="double",
    )
    experience = db.Column(
        db.Enum(*EXPERIENCE_LEVELS, name="settings_experience", native_enum=False),
        nullable=False,
        default="intermediate",
    )
    # The smallest load increase, per unit. Weights are prefilled in steps of this size.
    load_step_lb = db.Column(db.Float, nullable=False, default=5.0)
    load_step_kg = db.Column(db.Float, nullable=False, default=2.5)
    # Rep range used when an exercise in a template has none of its own, like "8-12".
    default_rep_range = db.Column(db.String(12), nullable=False, default="8-12")

    @classmethod
    def get(cls) -> "UserSettings":
        settings = db.session.get(cls, SETTINGS_SINGLETON_ID)
        if settings is None:
            settings = cls(id=SETTINGS_SINGLETON_ID)
            db.session.add(settings)
            db.session.commit()
        return settings
