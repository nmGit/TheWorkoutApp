from app.extensions import db
from app.models.constants import DISTANCE_UNITS, THEMES, WEIGHT_UNITS

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

    @classmethod
    def get(cls) -> "UserSettings":
        settings = db.session.get(cls, SETTINGS_SINGLETON_ID)
        if settings is None:
            settings = cls(id=SETTINGS_SINGLETON_ID)
            db.session.add(settings)
            db.session.commit()
        return settings
