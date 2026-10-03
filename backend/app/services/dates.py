"""Canonical UTC <-> server-local date handling.

`Workout.started_at`/`completed_at` (and similar) are always stored as
genuine UTC instants. But "which calendar day did this happen on" --
streaks, history grouping, date-range filters, "last performed" -- should
match the lifter's own sense of "today", which is the *server's local*
day (this is a self-hosted, single-user app; there's no per-user timezone
setting, so the server's own clock is the closest available proxy for
"the user's timezone" -- see docs/data_model.rst). A UTC calendar day and
a local one disagree for several hours out of every single day whenever
the server isn't in UTC, so this distinction is not an edge case.
"""
from datetime import date, datetime, timezone


def to_utc(dt: datetime) -> datetime:
    """A genuine UTC instant for `dt`.

    If `dt` is naive, Python's own `astimezone()` semantics already do
    exactly what's needed here: a naive datetime is presumed to represent
    the system's local wall clock, and is converted accordingly
    (correctly accounting for DST on that specific date, since the
    server's timezone is a real IANA zone, not a fixed offset). If `dt`
    is already aware, this just re-expresses it in UTC.
    """
    return dt.astimezone(timezone.utc)


def local_date(dt: datetime) -> date:
    """The calendar date `dt` falls on in the server's local timezone.

    `dt` is assumed to be a genuine UTC instant already (aware, or naive
    -- SQLAlchemy/SQLite hand back naive datetimes regardless of column
    declaration; see docs/data_migration.rst). A naive value is first
    explicitly marked UTC (not converted -- it already *is* UTC) before
    converting to local for the actual day-boundary computation.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date()


def local_midnight_utc(d: date) -> datetime:
    """Local midnight at the start of calendar date `d`, as a genuine UTC
    instant -- the inverse of local_date(), for building UTC-comparable
    range boundaries from a user-facing (local) date."""
    return datetime(d.year, d.month, d.day).astimezone(timezone.utc)
