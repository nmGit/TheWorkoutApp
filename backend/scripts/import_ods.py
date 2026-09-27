#!/usr/bin/env python3
"""One-off importer for the legacy Weightlifting.ods spreadsheet.

Usage:
    python scripts/import_ods.py /path/to/Weightlifting.ods

Refuses to run if any Workout already exists (not an ongoing sync — see
docs/data_migration.rst). Requires scripts/seed_exercises.py to have run
first, since exercises are matched by name rather than created here.
"""
import argparse
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from app import create_app
from app.extensions import db
from app.models.exercise import Exercise
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from scripts.ods_parser import ParsedGroup, parse_cell

MILES_TO_METERS = 1609.344


def load_sheet(path: str) -> pd.DataFrame:
    return pd.read_excel(path, engine="odf", sheet_name="Sheet1", header=None)


def _midnight_utc(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _add_sets_for_groups(workout_exercise: WorkoutExercise, groups: list[ParsedGroup]) -> int:
    position = 0
    for group in groups:
        if group.kind == "cardio":
            db.session.add(
                WorkoutSet(
                    workout_exercise_id=workout_exercise.id,
                    position=position,
                    duration_seconds=group.duration_seconds,
                    distance_meters=(
                        group.distance_miles * MILES_TO_METERS
                        if group.distance_miles is not None
                        else None
                    ),
                    completed=True,
                )
            )
            position += 1
        elif group.kind == "sets":
            for _ in range(group.sets):
                db.session.add(
                    WorkoutSet(
                        workout_exercise_id=workout_exercise.id,
                        position=position,
                        weight=group.weight,
                        weight_unit="lbs" if group.weight is not None else None,
                        reps=group.reps,
                        duration_seconds=group.duration_seconds,
                        is_dropset=group.is_dropset,
                        completed=True,
                    )
                )
                position += 1
        elif group.kind == "done":
            workout_exercise.notes = "Imported: marked done, no set data recorded."
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unknown group kind {group.kind}")
    return position


def import_workouts(path: str) -> None:
    if Workout.query.first() is not None:
        print("Refusing to import: Workout rows already exist. This importer is a one-time "
              "setup step, not an ongoing sync (see docs/data_migration.rst).")
        sys.exit(1)

    df = load_sheet(path)
    headers = df.iloc[1].tolist()

    exercise_by_name = {e.name: e for e in Exercise.query.all()}
    missing = set()

    workouts_created = 0
    sets_created = 0

    for row in range(2, df.shape[0]):
        raw_date = df.iat[row, 0]
        if pd.isna(raw_date):
            continue
        row_values = df.iloc[row, 1:]
        if row_values.isna().all():
            continue

        workout_date = pd.Timestamp(raw_date).date()
        workout = Workout(
            name="Workout",
            started_at=_midnight_utc(workout_date),
            completed_at=_midnight_utc(workout_date),
        )
        db.session.add(workout)
        db.session.flush()
        workouts_created += 1

        position = 0
        for col in range(1, df.shape[1]):
            cell = df.iat[row, col]
            if pd.isna(cell):
                continue
            name = headers[col]
            exercise = exercise_by_name.get(name)
            if exercise is None:
                missing.add(name)
                continue

            we = WorkoutExercise(
                workout_id=workout.id, exercise_id=exercise.id, position=position
            )
            db.session.add(we)
            db.session.flush()
            position += 1

            groups = parse_cell(str(cell))
            sets_created += _add_sets_for_groups(we, groups)
            db.session.flush()

    if missing:
        db.session.rollback()
        print("Aborting: no seeded Exercise found for column(s):", sorted(missing))
        print("Run scripts/seed_exercises.py first.")
        sys.exit(1)

    db.session.commit()
    print(f"Imported {workouts_created} workout(s), {sets_created} set(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ods_path", help="Path to the Weightlifting.ods file")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        import_workouts(args.ods_path)
