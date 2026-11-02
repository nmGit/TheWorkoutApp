#!/usr/bin/env python3
"""One-off backfill: ExerciseTemplate.tracking_type for already-seeded bodyweight-apparatus
exercises (catalog database only -- never touches a user's own CustomExerciseTemplate rows).

seed_exercise_templates.py sets tracking_type only when a template is first created ("app-owned,
set once") -- see app/services/exercise_templates.py's tracking_type_for_legacy/
tracking_type_for_repdb, both now fixed to call anything this app's own equipment classification
already calls "bodyweight" equipment (including a pull-up bar, a dip station, rings and a
suspension trainer -- not just moves needing literally no equipment) a bodyweight_reps exercise.
That fix only changes what a *future* reseed creates; every row already seeded as weight_reps
before the fix stays weight_reps until backfilled here, so its strength score / muscles-worked
display / 1RM silently floors at the exercise's usual 0 *added* weight instead of body weight +
added weight (see WorkoutSet.effective_weight).

Narrow and safe to re-run: only ever flips ExerciseTemplate.tracking_type from "weight_reps" to
"bodyweight_reps", and only where equipment == "bodyweight" -- never touches equipment, name, or
any other field, and never touches a cardio/time exercise (those never matched weight_reps to
begin with). Running it again after it's already fixed everything finds nothing left to change.

Usage:
    python scripts/backfill_bodyweight_tracking_type.py [--dry-run]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.exercise_template import ExerciseTemplate


def backfill(dry_run: bool = False) -> None:
    rows = ExerciseTemplate.query.filter_by(equipment="bodyweight", tracking_type="weight_reps").all()
    for row in rows:
        print(f"  {row.name!r} (id={row.id})")
        if not dry_run:
            row.tracking_type = "bodyweight_reps"

    if dry_run:
        print(f"\nWould backfill {len(rows)} exercise(s) (dry run -- nothing written).")
        return

    db.session.commit()
    print(f"\nBackfilled {len(rows)} exercise(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print what would change, without writing")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        backfill(dry_run=args.dry_run)
