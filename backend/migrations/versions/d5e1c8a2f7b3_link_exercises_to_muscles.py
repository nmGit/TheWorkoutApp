"""link exercises to a muscles table; remap every dataset muscle name

Revision ID: d5e1c8a2f7b3
Revises: b4a7d2e9c1f6
Create Date: 2026-10-05T01:18:53

Replaces the JSON primary_muscles/secondary_muscles columns with the muscles table and the
exercise_muscles link table. Every existing name is mapped to the specific muscles it means
(see services/muscle_catalog.py). The mapping is copied here so this migration never changes
when the app's catalog does.
"""

import json
import re

import sqlalchemy as sa
from alembic import op

revision = "d5e1c8a2f7b3"
down_revision = "b4a7d2e9c1f6"
branch_labels = None
depends_on = None

CANONICAL_MUSCLES = {
    "pectoralis_major": "Pectoralis Major",
    "upper_chest": "Upper Chest",
    "serratus_anterior": "Serratus Anterior",
    "latissimus_dorsi": "Latissimus Dorsi",
    "upper_back": "Upper Back",
    "rhomboids": "Rhomboids",
    "trapezius": "Trapezius",
    "levator_scapulae": "Levator Scapulae",
    "erector_spinae": "Erector Spinae",
    "quadratus_lumborum": "Quadratus Lumborum",
    "rotator_cuff": "Rotator Cuff",
    "anterior_deltoid": "Anterior Deltoid",
    "lateral_deltoid": "Lateral Deltoid",
    "posterior_deltoid": "Posterior Deltoid",
    "biceps_brachii": "Biceps Brachii",
    "brachialis": "Brachialis",
    "brachioradialis": "Brachioradialis",
    "triceps_brachii": "Triceps Brachii",
    "forearm_flexors": "Forearm Flexors",
    "forearm_extensors": "Forearm Extensors",
    "wrist_flexors": "Wrist Flexors",
    "wrist_extensors": "Wrist Extensors",
    "rectus_abdominis": "Rectus Abdominis",
    "transverse_abdominis": "Transverse Abdominis",
    "obliques": "Obliques",
    "gluteus_maximus": "Gluteus Maximus",
    "gluteus_medius": "Gluteus Medius",
    "adductors": "Adductors",
    "hamstrings": "Hamstrings",
    "quadriceps": "Quadriceps",
    "hip_flexors": "Hip Flexors",
    "gastrocnemius": "Gastrocnemius",
    "soleus": "Soleus",
    "tibialis": "Tibialis",
    "sternocleidomastoid": "Sternocleidomastoid",
}

RAW_TO_MUSCLES = {
    "abdominals": ['rectus_abdominis'],
    "abductors": ['gluteus_medius'],
    "abs": ['rectus_abdominis'],
    "adductors": ['adductors'],
    "ankle_stabilizers": [],
    "ankles": [],
    "anterior_deltoid": ['anterior_deltoid'],
    "back": ['upper_back'],
    "biceps": ['biceps_brachii'],
    "biceps_brachii": ['biceps_brachii'],
    "brachialis": ['brachialis'],
    "brachioradialis": ['brachioradialis'],
    "calves": ['gastrocnemius', 'soleus'],
    "cardiovascular_system": [],
    "chest": ['pectoralis_major'],
    "core": [],
    "deltoids": ['anterior_deltoid', 'lateral_deltoid', 'posterior_deltoid'],
    "delts": ['anterior_deltoid', 'lateral_deltoid', 'posterior_deltoid'],
    "erector_spinae": ['erector_spinae'],
    "feet": [],
    "forearm_extensors": ['forearm_extensors'],
    "forearm_flexors": ['forearm_flexors'],
    "forearms": ['forearm_flexors', 'forearm_extensors'],
    "gastrocnemius": ['gastrocnemius'],
    "glutes": ['gluteus_maximus'],
    "gluteus_maximus": ['gluteus_maximus'],
    "gluteus_medius": ['gluteus_medius'],
    "grip_muscles": ['forearm_flexors'],
    "groin": ['adductors'],
    "hamstring": ['hamstrings'],
    "hamstrings": ['hamstrings'],
    "hands": [],
    "head": [],
    "hip_flexors": ['hip_flexors'],
    "inner_quad": ['quadriceps'],
    "inner_thighs": ['adductors'],
    "knees": [],
    "lateral_deltoid": ['lateral_deltoid'],
    "lats": ['latissimus_dorsi'],
    "latissimus_dorsi": ['latissimus_dorsi'],
    "levator_scapulae": ['levator_scapulae'],
    "lower_abs": ['rectus_abdominis'],
    "lower_back": ['erector_spinae'],
    "lower_chest": ['pectoralis_major'],
    "lower_trapezius": ['trapezius'],
    "obliques": ['obliques'],
    "outer_quad": ['quadriceps'],
    "pectoralis_major": ['pectoralis_major'],
    "pectorals": ['pectoralis_major'],
    "posterior_deltoid": ['posterior_deltoid'],
    "quadratus_lumborum": ['quadratus_lumborum'],
    "quadriceps": ['quadriceps'],
    "quads": ['quadriceps'],
    "rear_deltoids": ['posterior_deltoid'],
    "rectus_abdominis": ['rectus_abdominis'],
    "rhomboids": ['rhomboids'],
    "rotator_cuff": ['rotator_cuff'],
    "serratus": ['serratus_anterior'],
    "serratus_anterior": ['serratus_anterior'],
    "shins": ['tibialis'],
    "shoulders": ['anterior_deltoid', 'lateral_deltoid', 'posterior_deltoid'],
    "soleus": ['soleus'],
    "spine": [],
    "sternocleidomastoid": ['sternocleidomastoid'],
    "neck": ['sternocleidomastoid'],
    "supraspinatus": ['rotator_cuff'],
    "transverse_abdominis": ['transverse_abdominis'],
    "trapezius": ['trapezius'],
    "traps": ['trapezius'],
    "upper_abs": ['rectus_abdominis'],
    "upper_back": ['upper_back'],
    "upper_chest": ['upper_chest'],
    "upper_trapezius": ['trapezius'],
    "triceps": ['triceps_brachii'],
    "triceps_brachii": ['triceps_brachii'],
    "wrist_extensors": ['wrist_extensors'],
    "wrist_flexors": ['wrist_flexors'],
    "wrists": ['wrist_flexors', 'wrist_extensors'],
    "full_body": [],
}


def _normalise(raw):
    return re.sub(r"[\s\-]+", "_", raw.strip().lower())


def _resolve(raw):
    key = _normalise(raw)
    if key in CANONICAL_MUSCLES:
        return [key]
    if key not in RAW_TO_MUSCLES:
        raise ValueError(f"No muscle mapping for dataset name {raw!r}")
    return RAW_TO_MUSCLES[key]


def upgrade():
    op.create_table(
        "muscles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(64), nullable=False),
    )
    op.create_table(
        "exercise_muscles",
        sa.Column("exercise_id", sa.Integer(), sa.ForeignKey("exercise_templates.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("muscle_id", sa.Integer(), sa.ForeignKey("muscles.id"), primary_key=True),
        sa.Column("role", sa.String(16), nullable=False),
    )
    muscles = sa.table("muscles", sa.column("id", sa.Integer), sa.column("slug", sa.String), sa.column("name", sa.String))
    op.bulk_insert(muscles, [{"slug": s, "name": n} for s, n in CANONICAL_MUSCLES.items()])

    conn = op.get_bind()
    muscle_id = {row.slug: row.id for row in conn.execute(sa.text("SELECT id, slug FROM muscles"))}
    rows = conn.execute(
        sa.text("SELECT id, primary_muscles, secondary_muscles FROM exercise_templates")
    ).fetchall()
    links = []
    for exercise_id, primary_json, secondary_json in rows:
        primary, secondary = [], []
        for raw in json.loads(primary_json or "[]"):
            primary += [s for s in _resolve(raw) if s not in primary]
        for raw in json.loads(secondary_json or "[]"):
            secondary += [s for s in _resolve(raw) if s not in secondary and s not in primary]
        for slug in primary:
            links.append({"exercise_id": exercise_id, "muscle_id": muscle_id[slug], "role": "primary"})
        for slug in secondary:
            links.append({"exercise_id": exercise_id, "muscle_id": muscle_id[slug], "role": "secondary"})
    if links:
        op.bulk_insert(sa.table("exercise_muscles", sa.column("exercise_id", sa.Integer), sa.column("muscle_id", sa.Integer), sa.column("role", sa.String)), links)

    with op.batch_alter_table("exercise_templates") as batch:
        batch.drop_column("primary_muscles")
        batch.drop_column("secondary_muscles")


def downgrade():
    with op.batch_alter_table("exercise_templates") as batch:
        batch.add_column(sa.Column("primary_muscles", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("secondary_muscles", sa.JSON(), nullable=True))
    conn = op.get_bind()
    slugs = {row.id: row.slug for row in conn.execute(sa.text("SELECT id, slug FROM muscles"))}
    for exercise_id, muscle_id, role in conn.execute(sa.text("SELECT exercise_id, muscle_id, role FROM exercise_muscles")).fetchall():
        column = "primary_muscles" if role == "primary" else "secondary_muscles"
        current = json.loads(conn.execute(sa.text(f"SELECT {column} FROM exercise_templates WHERE id = :id"), {"id": exercise_id}).scalar() or "[]")
        current.append(slugs[muscle_id])
        conn.execute(sa.text(f"UPDATE exercise_templates SET {column} = :v WHERE id = :id"), {"v": json.dumps(current), "id": exercise_id})
    op.drop_table("exercise_muscles")
    op.drop_table("muscles")
