"""Unit conversion helpers.

Weights/distances are stored per-entry in whatever unit they were logged
in (see docs/data_model.rst "Business rules"); these helpers convert to a
requested display unit on read without ever mutating stored values.
"""

LBS_PER_KG = 2.20462262185
METERS_PER_MILE = 1609.344
METERS_PER_KM = 1000.0


def convert_weight(value: float, from_unit: str, to_unit: str) -> float:
    if value is None or from_unit == to_unit:
        return value
    if from_unit == "lbs" and to_unit == "kg":
        return value / LBS_PER_KG
    if from_unit == "kg" and to_unit == "lbs":
        return value * LBS_PER_KG
    raise ValueError(f"Unknown weight unit conversion {from_unit} -> {to_unit}")


def meters_to_unit(meters: float, unit: str) -> float:
    if meters is None:
        return None
    if unit == "mi":
        return meters / METERS_PER_MILE
    if unit == "km":
        return meters / METERS_PER_KM
    raise ValueError(f"Unknown distance unit {unit}")


def unit_to_meters(value: float, unit: str) -> float:
    if value is None:
        return None
    if unit == "mi":
        return value * METERS_PER_MILE
    if unit == "km":
        return value * METERS_PER_KM
    raise ValueError(f"Unknown distance unit {unit}")
