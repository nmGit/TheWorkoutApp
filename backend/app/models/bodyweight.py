from app.extensions import db
from app.models.constants import WEIGHT_UNITS


class BodyweightEntry(db.Model):
    __tablename__ = "bodyweight_entries"

    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.Date, nullable=False, unique=True)
    weight = db.Column(db.Numeric(8, 4), nullable=False)
    unit = db.Column(
        db.Enum(*WEIGHT_UNITS, name="bodyweight_unit", native_enum=False), nullable=False
    )
