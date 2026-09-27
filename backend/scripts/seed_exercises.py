#!/usr/bin/env python3
"""Seed MuscleGroups and the built-in Exercise library.

Idempotent: running it again only adds muscle groups/exercises that don't
already exist by name, so it's safe to re-run after adding new entries to
seed_data/exercises.json. See docs/data_migration.rst.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.exercise import Exercise, MuscleGroup

SEED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data", "exercises.json")


def seed():
    with open(SEED_FILE) as f:
        data = json.load(f)

    groups_by_name = {}
    for order, name in enumerate(data["muscle_groups"]):
        group = MuscleGroup.query.filter_by(name=name).first()
        if group is None:
            group = MuscleGroup(name=name, display_order=order)
            db.session.add(group)
            db.session.flush()
            print(f"  + muscle group: {name}")
        groups_by_name[name] = group
    db.session.commit()

    created = 0
    for item in data["exercises"]:
        group = groups_by_name[item["muscle_group"]]
        existing = Exercise.query.filter_by(name=item["name"], muscle_group_id=group.id).first()
        if existing is not None:
            continue
        db.session.add(
            Exercise(
                name=item["name"],
                muscle_group_id=group.id,
                equipment=item["equipment"],
                tracking_type=item["tracking_type"],
                is_custom=False,
            )
        )
        created += 1
    db.session.commit()
    print(f"Seeded {created} new exercise(s) ({len(data['exercises'])} in seed file).")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
