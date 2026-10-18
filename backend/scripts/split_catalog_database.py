#!/usr/bin/env python3
"""One-time: split a combined workout.db into two databases.

- The shared catalog: every non-custom ``exercise_templates`` row, plus the ``muscles``/
  ``exercise_muscles``/``muscle_groups`` reference data those rows link to. Written to a new
  file (``catalog_db``), common to every user from here on.
- This user's own data: everything else, staying in ``user_db`` -- including the exercises that
  *were* custom ``exercise_templates`` rows, now moved into ``custom_exercise_templates`` (same
  ids, so every ``workout_exercises``/``template_exercises`` row that referenced one by id is
  simply repointed at ``custom_exercise_id`` instead of ``exercise_id``, no remapping needed),
  and any note on a catalog exercise, now in ``catalog_exercise_notes`` instead of a column on
  the (now shared) exercise itself.

Prerequisite: ``user_db`` must already be at the ``l0d3a8f5c2e9`` schema migration (run
``flask db upgrade`` first) -- this script only moves data, using plain sqlite3 rather than the
app's models, since those are wired for the *post*-split two-database world and this script runs
during the transition, while the catalog tables are still physically sitting in ``user_db``.

Deliberately NOT part of ``flask db upgrade``: this touches a second file the migration
framework doesn't manage, and Alembic migrations should only ever do schema, not a data move
like this. It is idempotent in the sense that re-running it recomputes from source and
overwrites the catalog file's content with CREATE-TABLE-if-missing + INSERT OR REPLACE, but it
is NOT safe to re-run after the follow-up migration has dropped the old catalog tables from
user_db -- there would be nothing left here to read.

Usage:
    python scripts/split_catalog_database.py <user_db> <catalog_db> [--apply]

Without --apply, only prints what it would do.
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS muscle_groups (
    id INTEGER PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    display_order INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS muscles (
    id INTEGER PRIMARY KEY,
    slug VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(64) NOT NULL
);
CREATE TABLE IF NOT EXISTS exercise_templates (
    id INTEGER PRIMARY KEY,
    external_id VARCHAR(16) UNIQUE,
    name VARCHAR(128) NOT NULL,
    category VARCHAR(64),
    body_part VARCHAR(64),
    equipment VARCHAR(64),
    equipment_raw VARCHAR(64),
    target_muscle VARCHAR(64),
    muscle_group VARCHAR(64),
    muscle_group_id INTEGER REFERENCES muscle_groups(id),
    tracking_type VARCHAR(15),
    instructions TEXT,
    instruction_steps JSON,
    image_path VARCHAR(255),
    attribution VARCHAR(255),
    created_at DATETIME NOT NULL,
    repdb_id VARCHAR(64) UNIQUE,
    repdb_images JSON,
    tips JSON,
    difficulty VARCHAR(16),
    mechanic VARCHAR(16),
    aliases JSON
);
CREATE TABLE IF NOT EXISTS exercise_muscles (
    exercise_id INTEGER REFERENCES exercise_templates(id) ON DELETE CASCADE,
    muscle_id INTEGER REFERENCES muscles(id),
    role VARCHAR(16) NOT NULL,
    PRIMARY KEY (exercise_id, muscle_id)
);
"""

# Columns copied straight across (same name, same meaning) from the source exercise_templates
# row into the catalog's -- i.e. everything except is_custom (gone -- implicitly always false in
# the catalog) and notes (moved to catalog_exercise_notes in user_db, not copied here at all).
CATALOG_EXERCISE_COLUMNS = [
    "id", "external_id", "name", "category", "body_part", "equipment", "equipment_raw",
    "target_muscle", "muscle_group", "muscle_group_id", "tracking_type", "instructions",
    "instruction_steps", "image_path", "attribution", "created_at", "repdb_id", "repdb_images",
    "tips", "difficulty", "mechanic", "aliases",
]


def _dict_rows(conn, sql, params=()):
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def split(user_db: str, catalog_db: str, apply: bool) -> None:
    src = sqlite3.connect(user_db)
    src.row_factory = sqlite3.Row

    required = {"custom_exercise_templates", "catalog_exercise_notes", "exercise_templates"}
    have = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = required - have
    if missing:
        sys.exit(f"{user_db} is missing {missing} -- run `flask db upgrade` on it first.")

    custom_rows = _dict_rows(src, "SELECT * FROM exercise_templates WHERE is_custom = 1")
    catalog_rows = _dict_rows(src, "SELECT * FROM exercise_templates WHERE is_custom = 0")
    muscle_group_rows = _dict_rows(src, "SELECT * FROM muscle_groups")
    muscle_rows = _dict_rows(src, "SELECT * FROM muscles")
    catalog_ids = {r["id"] for r in catalog_rows}
    exercise_muscle_rows = [
        r for r in _dict_rows(src, "SELECT * FROM exercise_muscles") if r["exercise_id"] in catalog_ids
    ]
    notes_to_move = [r for r in catalog_rows if (r["notes"] or "").strip()]

    already_custom = {r[0] for r in src.execute("SELECT id FROM custom_exercise_templates")}
    new_custom = [r for r in custom_rows if r["id"] not in already_custom]
    already_noted = {r[0] for r in src.execute("SELECT exercise_id FROM catalog_exercise_notes")}
    new_notes = [r for r in notes_to_move if r["id"] not in already_noted]

    we_to_repoint = _dict_rows(
        src,
        f"SELECT id, exercise_id FROM workout_exercises WHERE exercise_id IN "
        f"({','.join('?' * len(custom_rows))})" if custom_rows else "SELECT id, exercise_id FROM workout_exercises WHERE 0",
        tuple(r["id"] for r in custom_rows),
    )
    te_to_repoint = _dict_rows(
        src,
        f"SELECT id, exercise_id FROM template_exercises WHERE exercise_id IN "
        f"({','.join('?' * len(custom_rows))})" if custom_rows else "SELECT id, exercise_id FROM template_exercises WHERE 0",
        tuple(r["id"] for r in custom_rows),
    )

    print(f"Source: {user_db}")
    print(f"  catalog exercises to copy out:   {len(catalog_rows)} ({len(catalog_rows) - len(_existing_catalog_ids(catalog_db))} new if {catalog_db} already exists)")
    print(f"  muscle_groups / muscles / links: {len(muscle_group_rows)} / {len(muscle_rows)} / {len(exercise_muscle_rows)}")
    print(f"  custom exercises to move in:     {len(custom_rows)} ({len(new_custom)} not already present)")
    print(f"  catalog notes to move:           {len(notes_to_move)} ({len(new_notes)} not already present)")
    print(f"  workout_exercises to repoint:    {len(we_to_repoint)}")
    print(f"  template_exercises to repoint:   {len(te_to_repoint)}")

    if not apply:
        print("\nDry run only -- pass --apply to actually write.")
        return

    # 1. The catalog file.
    dst = sqlite3.connect(catalog_db)
    dst.executescript(CATALOG_SCHEMA)
    with dst:
        for r in muscle_group_rows:
            dst.execute(
                "INSERT OR REPLACE INTO muscle_groups (id, name, display_order) VALUES (?, ?, ?)",
                (r["id"], r["name"], r["display_order"]),
            )
        for r in muscle_rows:
            dst.execute(
                "INSERT OR REPLACE INTO muscles (id, slug, name) VALUES (?, ?, ?)",
                (r["id"], r["slug"], r["name"]),
            )
        for r in catalog_rows:
            cols = CATALOG_EXERCISE_COLUMNS
            dst.execute(
                f"INSERT OR REPLACE INTO exercise_templates ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                tuple(r[c] for c in cols),
            )
        for r in exercise_muscle_rows:
            dst.execute(
                "INSERT OR REPLACE INTO exercise_muscles (exercise_id, muscle_id, role) VALUES (?, ?, ?)",
                (r["exercise_id"], r["muscle_id"], r["role"]),
            )
    dst.close()
    print(f"Wrote {catalog_db}.")

    # 2. Move custom exercises + their muscles (flattened to JSON) into user_db's own table.
    import json

    with src:
        for r in new_custom:
            primary = [
                m["slug"]
                for m in _dict_rows(
                    src,
                    "SELECT m.slug FROM exercise_muscles em JOIN muscles m ON m.id = em.muscle_id "
                    "WHERE em.exercise_id = ? AND em.role = 'primary'",
                    (r["id"],),
                )
            ]
            secondary = [
                m["slug"]
                for m in _dict_rows(
                    src,
                    "SELECT m.slug FROM exercise_muscles em JOIN muscles m ON m.id = em.muscle_id "
                    "WHERE em.exercise_id = ? AND em.role = 'secondary'",
                    (r["id"],),
                )
            ]
            src.execute(
                "INSERT INTO custom_exercise_templates "
                "(id, name, equipment, tracking_type, muscle_group_id, notes, primary_muscles, secondary_muscles, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    r["id"], r["name"], r["equipment"], r["tracking_type"], r["muscle_group_id"],
                    r["notes"], json.dumps(primary), json.dumps(secondary), r["created_at"],
                ),
            )
        for r in new_notes:
            src.execute(
                "INSERT INTO catalog_exercise_notes (exercise_id, notes) VALUES (?, ?)",
                (r["id"], r["notes"].strip()),
            )
        for r in we_to_repoint:
            src.execute(
                "UPDATE workout_exercises SET custom_exercise_id = ?, exercise_id = NULL WHERE id = ?",
                (r["exercise_id"], r["id"]),
            )
        for r in te_to_repoint:
            src.execute(
                "UPDATE template_exercises SET custom_exercise_id = ?, exercise_id = NULL WHERE id = ?",
                (r["exercise_id"], r["id"]),
            )
    print(f"Updated {user_db}: {len(new_custom)} custom exercises, {len(new_notes)} notes, "
          f"{len(we_to_repoint)} workout_exercises + {len(te_to_repoint)} template_exercises repointed.")
    print(
        "\nThe old exercise_templates/exercise_muscles/muscles/muscle_groups tables are still "
        f"in {user_db} -- verify the new catalog works, then run the follow-up migration that "
        "drops them."
    )


def _existing_catalog_ids(catalog_db: str) -> set:
    if not os.path.exists(catalog_db):
        return set()
    conn = sqlite3.connect(catalog_db)
    try:
        return {r[0] for r in conn.execute("SELECT id FROM exercise_templates")}
    except sqlite3.OperationalError:
        return set()
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("user_db")
    parser.add_argument("catalog_db")
    parser.add_argument("--apply", action="store_true", help="Actually write; otherwise dry-run.")
    args = parser.parse_args()
    split(args.user_db, args.catalog_db, args.apply)
