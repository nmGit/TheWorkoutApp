#!/usr/bin/env python3
"""Seed ExerciseTemplate rows from the bundled exercises-dataset submodule.

Idempotent: rows are upserted by `external_id`, so re-running after the
submodule is updated (`git submodule update --remote external/exercises-dataset`)
only touches changed fields. Only the English instructions are imported;
the app displays templates in English only. See docs/data_migration.rst.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.exercise_template import ExerciseTemplate


def _dataset_file(app):
    dataset_dir = app.config["EXERCISE_DATASET_DIR"]
    path = os.path.join(dataset_dir, "data", "exercises.json")
    if not os.path.isfile(path):
        raise SystemExit(
            f"Dataset not found at {path}.\n"
            "Did you clone with submodules? Run:\n"
            "  git submodule update --init --recursive"
        )
    return path


def seed(app):
    with open(_dataset_file(app)) as f:
        records = json.load(f)

    created = 0
    updated = 0
    for item in records:
        external_id = item["id"]
        template = ExerciseTemplate.query.filter_by(external_id=external_id).first()
        is_new = template is None
        if is_new:
            template = ExerciseTemplate(external_id=external_id, is_custom=False)
            db.session.add(template)

        template.name = item["name"]
        template.category = item.get("category")
        template.body_part = item.get("body_part")
        template.equipment = item.get("equipment")
        template.target_muscle = item.get("target")
        template.muscle_group = item.get("muscle_group")
        template.secondary_muscles = item.get("secondary_muscles") or []
        template.instructions = item.get("instructions", {}).get("en")
        template.instruction_steps = item.get("instruction_steps", {}).get("en") or []
        template.image_path = item.get("image")
        template.attribution = item.get("attribution")

        if is_new:
            created += 1
        else:
            updated += 1

    db.session.commit()
    print(
        f"Seeded {created} new exercise template(s), updated {updated} existing "
        f"({len(records)} in dataset)."
    )


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed(app)
