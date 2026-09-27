"""Shared parsing for the legacy Weightlifting.ods spreadsheet.

See docs/source/data_migration.rst for the documented format and mapping
rules this module implements. Kept dependency-light (pandas/odfpy) and
separate from the main app so those deps don't leak into production
requirements.txt.
"""
import re
from dataclasses import dataclass, field

EQUIPMENT_ALIASES = {
    "barbell": "barbell",
    "dumbbell": "dumbbell",
    "db": "dumbbell",
    "cable": "cable",
    "machine": "machine",
    "bw": "bodyweight",
    "bodyweight": "bodyweight",
    "kettlebell": "kettlebell",
}

SET_RE = re.compile(
    r"^(?P<sets>\d+)\s*[×x]\s*(?P<amount>\d+(?:\.\d+)?)(?P<seconds>s)?"
    r"(?:\s*@\s*(?P<weight>\d+(?:\.\d+)?))?"
    r"(?P<drop>\s*drop)?$",
    re.IGNORECASE,
)
CARDIO_RE = re.compile(
    r"^(?P<minutes>\d+(?:\.\d+)?)\s*min(?:,\s*(?P<miles>\d+(?:\.\d+)?)\s*mi)?$",
    re.IGNORECASE,
)
CARDIO_DISTANCE_ONLY_RE = re.compile(
    r"^(?P<miles>\d+(?:\.\d+)?)\s*mi$", re.IGNORECASE
)
DONE_RE = re.compile(r"^done$", re.IGNORECASE)


def parse_equipment(column_name: str) -> str:
    m = re.search(r"\(([^)]+)\)\s*$", column_name)
    if not m:
        return "other"
    return EQUIPMENT_ALIASES.get(m.group(1).strip().lower(), "other")


@dataclass
class ParsedGroup:
    kind: str  # "sets" | "cardio" | "done"
    sets: int = 1
    reps: int | None = None
    duration_seconds: int | None = None
    weight: float | None = None
    distance_miles: float | None = None
    is_dropset: bool = False


def parse_cell(text: str) -> list[ParsedGroup]:
    """Parse one non-empty spreadsheet cell into its constituent set groups.

    A cell is either a single cardio duration(+distance) group (which may
    itself contain a comma, e.g. "15 min, 0.86 mi") or a comma-separated
    list of weight/rep set groups — never a mix, per the source format
    (see docs/data_migration.rst).
    """
    whole = str(text).strip()

    if DONE_RE.match(whole):
        return [ParsedGroup(kind="done")]

    m = CARDIO_RE.match(whole)
    if m:
        return [
            ParsedGroup(
                kind="cardio",
                duration_seconds=int(round(float(m.group("minutes")) * 60)),
                distance_miles=float(m.group("miles")) if m.group("miles") else None,
            )
        ]

    m = CARDIO_DISTANCE_ONLY_RE.match(whole)
    if m:
        return [ParsedGroup(kind="cardio", distance_miles=float(m.group("miles")))]

    groups = []
    for raw in whole.split(","):
        part = raw.strip()
        if not part:
            continue

        m = SET_RE.match(part)
        if not m:
            raise ValueError(f"Unrecognized cell fragment: {part!r} (full cell: {text!r})")

        is_seconds = bool(m.group("seconds"))
        groups.append(
            ParsedGroup(
                kind="sets",
                sets=int(m.group("sets")),
                reps=None if is_seconds else int(float(m.group("amount"))),
                duration_seconds=int(float(m.group("amount"))) if is_seconds else None,
                weight=float(m.group("weight")) if m.group("weight") else None,
                is_dropset=bool(m.group("drop")),
            )
        )

    return groups


def infer_tracking_type(category: str, cell_values: list[str]) -> str:
    if category == "Cardio":
        return "cardio"

    has_weight = False
    has_explicit_seconds = False
    only_bare_minutes = len(cell_values) > 0

    for text in cell_values:
        whole = str(text).strip()
        if DONE_RE.match(whole):
            continue
        if CARDIO_RE.match(whole) or CARDIO_DISTANCE_ONLY_RE.match(whole):
            continue
        only_bare_minutes = False
        for part in whole.split(","):
            part = part.strip()
            if not part:
                continue
            m = SET_RE.match(part)
            if m:
                if m.group("weight"):
                    has_weight = True
                if m.group("seconds"):
                    has_explicit_seconds = True

    if only_bare_minutes:
        return "time"
    if has_explicit_seconds and not has_weight:
        return "time"
    if has_weight:
        return "weight_reps"
    return "bodyweight_reps"
