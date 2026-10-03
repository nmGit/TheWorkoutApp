#!/usr/bin/env python3
"""Incremental importer for Strong app CSV exports.

Unlike scripts/import_ods.py (a one-time initial migration that refuses to
run against a non-empty database), this is meant to be re-run every time
you export a fresh CSV from Strong: it's idempotent per-workout-date, so
re-running it after logging a few more sessions in Strong only imports the
new ones. See docs/data_migration.rst for the full format writeup and the
exercise-matching rules this implements.

Usage:
    python scripts/import_strong_csv.py /path/to/strong_export.csv
"""
import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.dates import local_date, to_utc
from scripts.ods_parser import EQUIPMENT_ALIASES

NON_SET_ORDERS = {"Rest Timer", "Note"}


def normalize(name: str) -> str:
    base = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return re.sub(r"[^a-z0-9]", "", base.lower())


def parse_equipment_suffix(name: str) -> str | None:
    m = re.search(r"\(([^)]+)\)\s*$", name)
    return m.group(1) if m else None


def _f(value: str) -> float | None:
    return float(value) if value not in (None, "") else None


def _i(value: str) -> int | None:
    return int(round(float(value))) if value not in (None, "") else None


def load_rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def group_by_workout(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["Workout #"], []).append(r)
    return grouped


def resolve_exercise(name: str, cache: dict) -> ExerciseTemplate:
    """Match a Strong exercise name to an existing ExerciseTemplate row.

    Match order: exact name -> alias (a name the exercise is also known by)
    -> normalized base name (equipment reconciled to Strong's value, since
    it's the more precisely user-confirmed source).
    An exercise Strong knows about that we've never seen before isn't
    auto-created -- it's added to scripts/seed_data/exercises.json by hand
    first (see docs/data_migration.rst "Ongoing updates"), the same
    hand-reviewed-once policy as the rest of the seed data.
    """
    if name in cache:
        return cache[name]

    exact = ExerciseTemplate.query.filter(
        db.func.lower(ExerciseTemplate.name) == name.lower()
    ).first()
    if exact:
        cache[name] = exact
        return exact

    # An exercise that was merged into another (or is otherwise known by a
    # second name) lists the other names as aliases -- see
    # ExerciseTemplate.aliases.
    templates = ExerciseTemplate.query.all()
    lowered = name.lower()
    for template in templates:
        if any(alias.lower() == lowered for alias in (template.aliases or [])):
            cache[name] = template
            return template

    norm = normalize(name)
    candidates = [e for e in templates if normalize(e.name) == norm]
    strong_equip = parse_equipment_suffix(name)
    if len(candidates) == 1:
        match = candidates[0]
        resolved_equip = _resolve_equipment(strong_equip) if strong_equip else None
        if resolved_equip and resolved_equip != match.equipment:
            print(f"  Correcting {match.name!r} equipment: {match.equipment} -> {resolved_equip} "
                  f"(per Strong export)")
            match.equipment = resolved_equip
        cache[name] = match
        return match

    raise LookupError(
        f"No existing exercise matches {name!r} (normalized: {norm!r}). "
        f"Add it to scripts/seed_data/exercises.json and re-run scripts/seed_exercise_templates.py first."
    )


def _resolve_equipment(raw: str) -> str:
    lowered = raw.lower()
    if lowered in EQUIPMENT_ALIASES:
        return EQUIPMENT_ALIASES[lowered]
    for alias, canonical in EQUIPMENT_ALIASES.items():
        if lowered.startswith(alias):
            return canonical
    return "other"


def import_workouts(path: str) -> None:
    rows = load_rows(path)
    grouped = group_by_workout(rows)

    existing_dates = {
        local_date(w.started_at).isoformat()
        for w in Workout.query.filter(Workout.completed_at.isnot(None)).all()
    }

    exercise_cache: dict[str, ExerciseTemplate] = {}
    imported = 0
    skipped = 0
    sets_created = 0

    for workout_num in sorted(grouped, key=int):
        workout_rows = grouped[workout_num]
        # Strong exports timestamps in the device's local wall-clock time
        # (this app's server timezone, for a self-hosted single-user app --
        # see app/services/dates.py), not UTC, so this must be properly
        # converted rather than just labelled UTC.
        started_at = to_utc(datetime.strptime(workout_rows[0]["Date"], "%Y-%m-%d %H:%M:%S"))
        if local_date(started_at).isoformat() in existing_dates:
            skipped += 1
            continue

        duration = _i(workout_rows[0]["Duration (sec)"]) or 0
        workout = Workout(
            name=workout_rows[0]["Workout Name"] or "Workout",
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=duration),
            notes=workout_rows[0]["Workout Notes"] or None,
        )
        db.session.add(workout)
        db.session.flush()

        exercises_in_order: list[str] = []
        rows_by_exercise: dict[str, list[dict]] = {}
        for r in workout_rows:
            ex_name = r["Exercise Name"]
            if ex_name not in rows_by_exercise:
                rows_by_exercise[ex_name] = []
                exercises_in_order.append(ex_name)
            rows_by_exercise[ex_name].append(r)

        for position, ex_name in enumerate(exercises_in_order):
            ex_rows = rows_by_exercise[ex_name]
            exercise = resolve_exercise(ex_name, exercise_cache)

            note_text = " / ".join(
                r["Notes"] for r in ex_rows if r["Set Order"] == "Note" and r["Notes"]
            ) or None

            we = WorkoutExercise(
                workout_id=workout.id, exercise_id=exercise.id, position=position, notes=note_text
            )
            db.session.add(we)
            db.session.flush()

            set_position = 0
            for r in ex_rows:
                if r["Set Order"] in NON_SET_ORDERS:
                    continue
                db.session.add(
                    WorkoutSet(
                        workout_exercise_id=we.id,
                        position=set_position,
                        weight=_f(r["Weight (kg)"]),
                        weight_unit="kg" if _f(r["Weight (kg)"]) is not None else None,
                        reps=_i(r["Reps"]),
                        duration_seconds=_i(r["Seconds"]),
                        distance_meters=_f(r["Distance (meters)"]),
                        is_dropset=r["Set Order"] == "D",
                        rpe=_f(r["RPE"]),
                        completed=True,
                    )
                )
                set_position += 1
                sets_created += 1

        imported += 1
        print(f"  Imported {local_date(started_at)} — {workout.name!r} ({len(exercises_in_order)} exercises)")

    db.session.commit()
    print(f"\nImported {imported} new workout(s), {sets_created} set(s). "
          f"Skipped {skipped} workout(s) already in the database.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="Path to the Strong CSV export")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        import_workouts(args.csv_path)
