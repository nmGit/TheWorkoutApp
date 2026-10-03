#!/usr/bin/env python3
"""One-off backfill: real workout names/timestamps from a Strong CSV export.

Workouts imported by the retired scripts/import_ods.py all share the
generic name "Workout" and a midnight start time with zero duration,
since the spreadsheet had neither (see docs/data_migration.rst's "Known
limitations" for the spreadsheet importer). Strong's own export has both
for every workout it knows about -- including the ones the spreadsheet
already covered -- so this fixes those two fields by matching on date,
against whatever workouts are already in the database.

Deliberately narrow scope: this only ever updates Workout.name,
started_at, and completed_at. It never touches WorkoutExercise or
WorkoutSet rows, so it can't clobber a set edited by hand through the app
since the original import. Safe to re-run.

Usage:
    python scripts/backfill_workout_names.py /path/to/strong_export.csv
"""
import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.workout import Workout
from app.services.dates import local_date, to_utc
from scripts.import_strong_csv import _i, group_by_workout, load_rows


def backfill(path: str) -> None:
    rows = load_rows(path)
    grouped = group_by_workout(rows)

    by_date: dict[str, tuple[str, datetime, datetime]] = {}
    for workout_rows in grouped.values():
        # Strong exports local wall-clock time, not UTC -- see the matching
        # comment in scripts/import_strong_csv.py.
        started_at = to_utc(datetime.strptime(workout_rows[0]["Date"], "%Y-%m-%d %H:%M:%S"))
        duration = _i(workout_rows[0]["Duration (sec)"]) or 0
        name = workout_rows[0]["Workout Name"] or "Workout"
        by_date[local_date(started_at).isoformat()] = (name, started_at, started_at + timedelta(seconds=duration))

    renamed = 0
    retimed = 0
    unchanged = 0
    unmatched = []

    for workout in Workout.query.filter(Workout.completed_at.isnot(None)).all():
        key = local_date(workout.started_at).isoformat()
        if key not in by_date:
            unmatched.append(key)
            continue

        name, started_at, completed_at = by_date[key]
        changed = False

        if workout.name != name:
            print(f"  {key}: {workout.name!r} -> {name!r}")
            workout.name = name
            renamed += 1
            changed = True

        # SQLite always hands back naive datetimes regardless of the
        # DateTime(timezone=True) column declaration, so compare against
        # naive versions of the CSV values or every run would look "changed".
        if (
            workout.started_at != started_at.replace(tzinfo=None)
            or workout.completed_at != completed_at.replace(tzinfo=None)
        ):
            workout.started_at = started_at
            workout.completed_at = completed_at
            retimed += 1
            changed = True

        if not changed:
            unchanged += 1

    db.session.commit()
    print(f"\nRenamed {renamed}, re-timed {retimed}, already correct {unchanged}.")
    if unmatched:
        print(f"No CSV match for {len(unmatched)} workout date(s) (left untouched): {unmatched}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="Path to the Strong CSV export")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        backfill(args.csv_path)
