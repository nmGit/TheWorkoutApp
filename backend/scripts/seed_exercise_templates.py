#!/usr/bin/env python3
"""Seed ExerciseTemplate rows from the two bundled exercise datasets.

Two git submodules feed the catalog (see docs/source/features/exercise_library.rst):

- ``external/exercises-dataset`` (the original, "legacy" source: 1,324 entries,
  one grainy image each), and
- ``external/repdb-exercise-dataset`` (RepDB, https://repdb.co: 609 entries,
  clean two-pose illustrations, tips, muscle data).

Each source's data is stored on the template as that source provides it;
RepDB's images/text/muscles win wherever RepDB covers an exercise, and the
legacy source stays as the fallback everywhere else.

Idempotent and safe to re-run (e.g. after ``git submodule update --remote``)
because of one ownership rule: fields the user can edit in the app -- name,
equipment, tracking_type, muscle_group_id, notes, is_custom -- are set only
when this script *creates* a row, never on a re-run. Re-runs refresh only the
dataset-owned fields (instructions, images, tips, attribution, muscles, ...).

How a RepDB entry finds its template, in priority order:

1. the template already carries its ``repdb_id`` (every re-run);
2. ``seed_data/repdb_mapping.json`` -- hand-reviewed links by template name
   (a null value means "checked, no equivalent", and also blocks 3);
3. exact *word-set* equality between names ("dumbbell bent over row" ==
   "Bent-Over Dumbbell Row"), only if unambiguous;
4. otherwise a new template is created from the RepDB entry.

Each RepDB id is claimed by at most one template; a second claimant keeps its
original content (reported as a collision). Fuzzy/near matches are never
auto-linked -- they're listed in a "possible duplicates" report instead.

Usage:
    python scripts/seed_exercise_templates.py --dry-run   # report only, writes nothing
    python scripts/seed_exercise_templates.py
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.exercise import MuscleGroup
from app.models.exercise_template import ExerciseTemplate
from app.services.exercise_templates import (
    equipment_type_for,
    equipment_type_for_repdb,
    muscle_group_name_for_body_part,
    muscle_group_name_for_repdb,
    tracking_type_for_repdb,
)

SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data")
CURATED_FILE = os.path.join(SEED_DIR, "exercises.json")
REPDB_MAPPING_FILE = os.path.join(SEED_DIR, "repdb_mapping.json")

REPDB_ATTRIBUTION = "Exercise data by RepDB (repdb.co) — https://repdb.co"

_STOPWORDS = {"the", "a", "of", "and", "with", "on", "to"}
_KEEP_TRAILING_S = {"press", "class", "biceps", "triceps", "abs", "glutes"}


def name_tokens(name: str) -> frozenset:
    """Order-insensitive, hyphen/punctuation/plural-insensitive word set."""
    s = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("-", " ").replace("'", ""))
    words = []
    for w in s.split():
        if w in _STOPWORDS:
            continue
        if w.endswith("s") and len(w) > 3 and w not in _KEEP_TRAILING_S:
            w = w[:-1]
        words.append(w)
    return frozenset(words)


def _load_json(path, what):
    if not os.path.isfile(path):
        raise SystemExit(
            f"{what} not found at {path}.\n"
            "Did you clone with submodules? Run:\n"
            "  git submodule update --init --recursive"
        )
    with open(path) as f:
        return json.load(f)


def seed_muscle_groups(summary):
    data = _load_json(CURATED_FILE, "Curated exercise list")
    for order, name in enumerate(data["muscle_groups"]):
        if MuscleGroup.query.filter_by(name=name).first() is None:
            db.session.add(MuscleGroup(name=name, display_order=order))
            summary["muscle_groups_created"] += 1
    db.session.flush()


def _muscle_group_id(name):
    group = MuscleGroup.query.filter_by(name=name).first() if name else None
    return group.id if group else None


def seed_legacy(app, summary):
    """The original dataset. Returns {lowercased name: template} for rows
    created in this run (the only rows the curated overrides may touch)."""
    records = _load_json(
        os.path.join(app.config["EXERCISE_DATASET_DIR"], "data", "exercises.json"),
        "Original exercise dataset",
    )
    created = {}
    for item in records:
        template = ExerciseTemplate.query.filter_by(external_id=item["id"]).first()
        if template is None:
            body_part = item.get("body_part")
            template = ExerciseTemplate(
                external_id=item["id"],
                is_custom=False,
                # App-owned fields: set once, here, and never again.
                name=item["name"],
                equipment=equipment_type_for(item.get("equipment")),
                muscle_group_id=_muscle_group_id(muscle_group_name_for_body_part(body_part)),
                tracking_type="cardio" if body_part == "cardio" else "weight_reps",
            )
            db.session.add(template)
            created[item["name"].lower()] = template
            summary["legacy_created"] += 1
        else:
            summary["legacy_updated"] += 1

        # Dataset-owned fields: refreshed on every run.
        template.category = item.get("category")
        template.body_part = item.get("body_part")
        template.equipment_raw = item.get("equipment")
        template.target_muscle = item.get("target")
        template.muscle_group = item.get("muscle_group")
        template.image_path = item.get("image")
        # ... except the ones RepDB supersedes once it has claimed the row.
        if template.repdb_id is None:
            template.instructions = item.get("instructions", {}).get("en")
            template.instruction_steps = item.get("instruction_steps", {}).get("en") or []
            template.attribution = item.get("attribution")
            template.primary_muscles = [item["target"]] if item.get("target") else []
            template.secondary_muscles = item.get("secondary_muscles") or []
    db.session.flush()
    return created


def seed_curated(created_legacy, summary):
    """Hand-curated exercises.json. On a fresh install this gives the user's
    own exercise names; on an existing database every name already exists, so
    it only ever touches rows this very run created."""
    data = _load_json(CURATED_FILE, "Curated exercise list")
    for item in data["exercises"]:
        group_id = _muscle_group_id(item["muscle_group"])
        target = created_legacy.get(item["name"].lower())
        if target is None:
            if ExerciseTemplate.query.filter_by(name=item["name"]).first() is not None:
                continue
            target = ExerciseTemplate(name=item["name"], is_custom=True)
            db.session.add(target)
            summary["curated_created"] += 1
        else:
            summary["curated_overrides"] += 1
        target.muscle_group_id = group_id
        target.equipment = item["equipment"]
        target.tracking_type = item["tracking_type"]
    db.session.flush()


def _apply_repdb_fields(template, item):
    """RepDB-owned fields: set on claim/insert and refreshed on every re-run."""
    images = item.get("images", {}).get("flat", {})
    ordered = [images[k] for k in ("start", "peak", "main") if k in images]
    steps = item.get("instructions_en") or []
    template.repdb_id = item["id"]
    template.repdb_images = ordered
    template.instruction_steps = steps
    template.instructions = " ".join(steps)
    template.tips = item.get("tips_en") or []
    template.difficulty = item.get("difficulty")
    template.mechanic = item.get("mechanic")
    template.primary_muscles = item.get("primary_muscles") or []
    template.secondary_muscles = item.get("secondary_muscles") or []
    template.attribution = REPDB_ATTRIBUTION


def seed_repdb(app, summary):
    data = _load_json(
        os.path.join(app.config["REPDB_DATASET_DIR"], "exercises.json"), "RepDB dataset"
    )
    records = {r["id"]: r for r in data["exercises"]}
    mapping = _load_json(REPDB_MAPPING_FILE, "RepDB mapping")["name_to_repdb_id"]

    for name, slug in mapping.items():
        if slug is not None and slug not in records:
            raise SystemExit(f"repdb_mapping.json: {name!r} -> {slug!r} is not in the RepDB dataset")

    templates = ExerciseTemplate.query.order_by(ExerciseTemplate.id).all()
    claimed = {t.repdb_id: t for t in templates if t.repdb_id}  # slug -> template
    unclaimed = [t for t in templates if t.repdb_id is None]

    def claim(template, slug, how):
        if slug in claimed and claimed[slug] is not template:
            summary["collisions"].append(
                f"{template.name!r} also wanted {slug!r}, already claimed by {claimed[slug].name!r}"
            )
            return
        claimed[slug] = template
        _apply_repdb_fields(template, records[slug])
        summary[f"repdb_claimed_{how}"] += 1
        summary["matches"].append((how, template.name, records[slug]["name_en"]))

    # 2. hand-reviewed mapping (first template with that exact name)
    seen_mapped_names = set()
    for template in unclaimed:
        if template.name in mapping and template.name not in seen_mapped_names:
            seen_mapped_names.add(template.name)
            if mapping[template.name] is not None:
                claim(template, mapping[template.name], "mapping")
    # 3. unambiguous word-set equality, for templates the mapping doesn't cover
    by_tokens = {}
    for slug, record in records.items():
        if slug not in claimed:
            by_tokens.setdefault(name_tokens(record["name_en"]), []).append(slug)
    for template in unclaimed:
        if template.repdb_id is not None or template.name in mapping:
            continue
        candidates = by_tokens.get(name_tokens(template.name), [])
        if len(candidates) == 1:
            claim(template, candidates[0], "wordset")
        elif len(candidates) > 1:
            summary["collisions"].append(
                f"{template.name!r} matches several RepDB entries {candidates}; left alone"
            )

    # refresh every already-claimed template (re-runs after a dataset update)
    for slug, template in claimed.items():
        if template.repdb_id == slug and (slug in records):
            _apply_repdb_fields(template, records[slug])

    # 4. everything RepDB covers that no template claimed becomes a new template
    new_templates = []
    for slug, record in records.items():
        if slug in claimed:
            continue
        template = ExerciseTemplate(
            is_custom=False,
            # App-owned fields: set once, here, and never again.
            name=record["name_en"],
            equipment=equipment_type_for_repdb(record.get("equipment")),
            muscle_group_id=_muscle_group_id(
                muscle_group_name_for_repdb(record.get("category"), record.get("body_part"))
            ),
            tracking_type=tracking_type_for_repdb(record),
            # RepDB's own vocabulary, kept for reference like the legacy columns.
            category=record.get("category"),
            body_part=record.get("body_part"),
            equipment_raw=record.get("equipment"),
        )
        _apply_repdb_fields(template, record)
        db.session.add(template)
        new_templates.append(template)
        summary["repdb_created"] += 1
    db.session.flush()

    # Report near-twins instead of guessing: a new RepDB template whose name is
    # very close to an existing template that RepDB did not claim.
    leftovers = [(t, name_tokens(t.name)) for t in templates if t.repdb_id is None]
    for new in new_templates:
        a = name_tokens(new.name)
        best = max(
            ((len(a & tokens) / len(a | tokens), t) for t, tokens in leftovers),
            key=lambda x: x[0],
            default=(0, None),
        )
        if best[0] >= 0.75:
            summary["possible_duplicates"].append((new.name, best[1].name, round(best[0], 2)))


def seed(app, dry_run=False):
    summary = {
        k: 0
        for k in (
            "muscle_groups_created",
            "legacy_created",
            "legacy_updated",
            "curated_created",
            "curated_overrides",
            "repdb_claimed_mapping",
            "repdb_claimed_wordset",
            "repdb_created",
        )
    }
    summary.update(collisions=[], matches=[], possible_duplicates=[])

    seed_muscle_groups(summary)
    created_legacy = seed_legacy(app, summary)
    seed_curated(created_legacy, summary)
    seed_repdb(app, summary)

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()
    return summary


def print_summary(summary, dry_run):
    print(("DRY RUN -- nothing was written.\n" if dry_run else "") + "Matched to existing templates:")
    for how, ours, theirs in sorted(summary["matches"]):
        print(f"  [{how:8}] {ours!r:56} <-> RepDB {theirs!r}")
    if summary["collisions"]:
        print("\nCollisions / ambiguities (left alone):")
        for line in summary["collisions"]:
            print("  " + line)
    if summary["possible_duplicates"]:
        print(f"\nPossible duplicates ({len(summary['possible_duplicates'])}) -- new RepDB entry vs. an "
              "unmatched existing one; review and merge by hand if they're the same exercise:")
        for new, old, score in summary["possible_duplicates"]:
            print(f"  {new!r} ~ {old!r} ({score})")
    print("\nTotals:")
    for key, value in summary.items():
        if isinstance(value, int):
            print(f"  {key}: {value}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Report what would change; write nothing")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print_summary(seed(app, dry_run=args.dry_run), args.dry_run)
