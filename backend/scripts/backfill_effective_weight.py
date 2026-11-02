#!/usr/bin/env python3
"""One-off backfill: WorkoutSet.effective_weight for rows that predate the column.

migrations/versions/n2f5c0b7e4a1_effective_weight.py only adds the column -- every
already-existing row starts out NULL, the same as "weight was entered before this column
existed" looks from the schema's point of view. This fills them in using the exact same
computation the ``before_insert``/``before_update`` mapper event uses for every write from
here on (see WorkoutSet.effective_weight) -- it has to be run once, directly, since a bulk
``UPDATE`` never constructs ORM objects (so the event never fires for it), and even loading
every row and re-saving it unchanged wouldn't trigger the event either (SQLAlchemy only
fires ``before_update`` on a column that's actually dirty).

Safe to re-run: every row's effective_weight is simply recomputed from its own weight plus
the body-weight log as of its workout's date -- the same inputs the event already used, and
nothing here depends on effective_weight's own previous value.

Usage:
    python scripts/backfill_effective_weight.py [--dry-run]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.workout import WorkoutSet, _compute_effective_weight


def backfill(dry_run: bool = False) -> None:
    sets = WorkoutSet.query.all()
    changed = 0
    for s in sets:
        computed = _compute_effective_weight(s)
        current = s.effective_weight
        if current is None or computed is None:
            different = current != computed
        else:
            # Decimal (from the DB) vs. float (just computed) -- compare as float to avoid a
            # spurious "changed" on every row from representation differences alone.
            different = round(float(current), 4) != round(float(computed), 4)
        if different:
            changed += 1
            if not dry_run:
                s.effective_weight = computed

    if dry_run:
        print(f"Would backfill {changed} of {len(sets)} set(s) (dry run -- nothing written).")
        return

    db.session.commit()
    print(f"Backfilled {changed} of {len(sets)} set(s) (the rest already matched).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print what would change, without writing")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        backfill(dry_run=args.dry_run)
