"""The muscles the app knows about, and how the names in the exercise datasets map onto them.

Every exercise links to zero or more rows of the `muscles` table, so a muscle has exactly one
row and can't be named two ways. Body regions ("chest", "legs", "core") are not muscles and
never appear here. Dataset names for a region are mapped to the specific muscles they cover,
and names with no single muscle (for example "core" or "cardiovascular_system") map to none.
"""

# Canonical muscle slug -> display name.
CANONICAL_MUSCLES: dict[str, str] = {
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

_DELTOIDS = ["anterior_deltoid", "lateral_deltoid", "posterior_deltoid"]

# Normalised dataset name (lower case, underscores) -> the canonical muscles it means.
# An empty list means the name names no single muscle.
RAW_TO_MUSCLES: dict[str, list[str]] = {
    "abdominals": ["rectus_abdominis"],
    "abductors": ["gluteus_medius"],
    "abs": ["rectus_abdominis"],
    "adductors": ["adductors"],
    "ankle_stabilizers": [],
    "ankles": [],
    "anterior_deltoid": ["anterior_deltoid"],
    "back": ["upper_back"],
    "biceps": ["biceps_brachii"],
    "biceps_brachii": ["biceps_brachii"],
    "brachialis": ["brachialis"],
    "brachioradialis": ["brachioradialis"],
    "calves": ["gastrocnemius", "soleus"],
    "cardiovascular_system": [],
    "chest": ["pectoralis_major"],
    "core": [],
    "deltoids": _DELTOIDS,
    "delts": _DELTOIDS,
    "erector_spinae": ["erector_spinae"],
    "feet": [],
    "forearm_extensors": ["forearm_extensors"],
    "forearm_flexors": ["forearm_flexors"],
    "forearms": ["forearm_flexors", "forearm_extensors"],
    "gastrocnemius": ["gastrocnemius"],
    "glutes": ["gluteus_maximus"],
    "gluteus_maximus": ["gluteus_maximus"],
    "gluteus_medius": ["gluteus_medius"],
    "grip_muscles": ["forearm_flexors"],
    "groin": ["adductors"],
    "hamstring": ["hamstrings"],
    "hamstrings": ["hamstrings"],
    "hands": [],
    "head": [],
    "hip_flexors": ["hip_flexors"],
    "inner_quad": ["quadriceps"],
    "inner_thighs": ["adductors"],
    "knees": [],
    "lateral_deltoid": ["lateral_deltoid"],
    "lats": ["latissimus_dorsi"],
    "latissimus_dorsi": ["latissimus_dorsi"],
    "levator_scapulae": ["levator_scapulae"],
    "lower_abs": ["rectus_abdominis"],
    "lower_back": ["erector_spinae"],
    "lower_chest": ["pectoralis_major"],
    "lower_trapezius": ["trapezius"],
    "obliques": ["obliques"],
    "outer_quad": ["quadriceps"],
    "pectoralis_major": ["pectoralis_major"],
    "pectorals": ["pectoralis_major"],
    "posterior_deltoid": ["posterior_deltoid"],
    "quadratus_lumborum": ["quadratus_lumborum"],
    "quadriceps": ["quadriceps"],
    "quads": ["quadriceps"],
    "rear_deltoids": ["posterior_deltoid"],
    "rectus_abdominis": ["rectus_abdominis"],
    "rhomboids": ["rhomboids"],
    "rotator_cuff": ["rotator_cuff"],
    "serratus": ["serratus_anterior"],
    "serratus_anterior": ["serratus_anterior"],
    "shins": ["tibialis"],
    "shoulders": _DELTOIDS,
    "soleus": ["soleus"],
    "spine": [],
    "sternocleidomastoid": ["sternocleidomastoid"],
    "neck": ["sternocleidomastoid"],
    "supraspinatus": ["rotator_cuff"],
    "transverse_abdominis": ["transverse_abdominis"],
    "trapezius": ["trapezius"],
    "traps": ["trapezius"],
    "upper_abs": ["rectus_abdominis"],
    "upper_back": ["upper_back"],
    "upper_chest": ["upper_chest"],
    "upper_trapezius": ["trapezius"],
    "triceps": ["triceps_brachii"],
    "triceps_brachii": ["triceps_brachii"],
    "wrist_extensors": ["wrist_extensors"],
    "wrist_flexors": ["wrist_flexors"],
    "wrists": ["wrist_flexors", "wrist_extensors"],
    "full_body": [],
}


def normalise(raw: str) -> str:
    """The key a dataset name is looked up by: lower case, separators as underscores."""
    import re

    return re.sub(r"[\s\-]+", "_", raw.strip().lower())


def resolve(raw: str) -> list[str]:
    """The canonical muscles a dataset name means. Unknown names raise, so nothing is silently
    dropped."""
    key = normalise(raw)
    if key in CANONICAL_MUSCLES:
        return [key]
    if key not in RAW_TO_MUSCLES:
        raise ValueError(f"No muscle mapping for dataset name {raw!r}")
    return list(RAW_TO_MUSCLES[key])
