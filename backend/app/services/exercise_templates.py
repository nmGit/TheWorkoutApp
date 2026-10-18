"""Maps exercises-dataset vocabulary onto this app's native Exercise fields.

The bundled dataset (external/exercises-dataset) uses its own body-part and
equipment vocabulary, which doesn't line up 1:1 with this app's fixed
MuscleGroup list (seeded from the original spreadsheet) or its EQUIPMENT_TYPES
enum. These tables translate a template's `body_part`/`equipment` into the
closest native value when an Exercise is created from a template.
"""

# dataset body_part -> this app's MuscleGroup.name
BODY_PART_TO_MUSCLE_GROUP = {
    "chest": "Chest",
    "back": "Back",
    "shoulders": "Shoulders",
    "neck": "Shoulders",
    "upper arms": "Arms",
    "lower arms": "Arms",
    "upper legs": "Legs",
    "lower legs": "Legs",
    "waist": "Core",
    "cardio": "Cardio",
}

# dataset equipment -> this app's EQUIPMENT_TYPES enum
EQUIPMENT_TO_TYPE = {
    "body weight": "bodyweight",
    "dumbbell": "dumbbell",
    "cable": "cable",
    "kettlebell": "kettlebell",
    "barbell": "barbell",
    "ez barbell": "barbell",
    "olympic barbell": "barbell",
    "trap bar": "barbell",
    "leverage machine": "machine",
    "smith machine": "machine",
    "sled machine": "machine",
    "skierg machine": "machine",
    "stationary bike": "machine",
    "elliptical machine": "machine",
    "stepmill machine": "machine",
    "upper body ergometer": "machine",
}


def muscle_group_name_for_body_part(body_part: str | None) -> str | None:
    if not body_part:
        return None
    return BODY_PART_TO_MUSCLE_GROUP.get(body_part.lower())


def body_parts_for_muscle_group(muscle_group_name: str) -> list[str]:
    """Reverse of BODY_PART_TO_MUSCLE_GROUP: every dataset body_part that
    maps onto this app's given MuscleGroup name. Used to filter the
    dataset-sourced template catalog by this app's own muscle group list
    (Full Body/Mobility have no dataset body_part and always return [])."""
    return [bp for bp, mg in BODY_PART_TO_MUSCLE_GROUP.items() if mg == muscle_group_name]


# The muscles each muscle group is made of, as canonical slugs (see
# canonical_muscle_slug in serializers.py). The exercise library offers these as the
# sub-filter under a group. It's a fixed list, not whatever happens to be primary in
# that group's exercises: a glute bridge press filed under chest must not put
# gluteus under Chest. Groups not listed here (Full Body, Cardio, Mobility) get no
# sub-filter.
GROUP_MUSCLES = {
    "Chest": {"pectoralis_major", "upper_chest", "serratus_anterior"},
    "Back": {
        "latissimus_dorsi", "upper_back", "rhomboids", "trapezius",
        "levator_scapulae", "erector_spinae", "quadratus_lumborum",
    },
    "Shoulders": {"anterior_deltoid", "lateral_deltoid", "posterior_deltoid", "rotator_cuff"},
    "Arms": {
        "biceps_brachii", "brachialis", "brachioradialis", "triceps_brachii",
        "forearm_flexors", "forearm_extensors", "wrist_flexors", "wrist_extensors",
    },
    "Core": {"rectus_abdominis", "transverse_abdominis", "obliques"},
    "Legs": {
        "quadriceps", "hamstrings", "gluteus_maximus", "gluteus_medius", "adductors",
        "hip_flexors", "gastrocnemius", "soleus", "tibialis",
    },
}


def equipment_type_for(equipment: str | None) -> str:
    if not equipment:
        return "other"
    return EQUIPMENT_TO_TYPE.get(equipment.lower(), "other")


# --- RepDB (external/repdb-exercise-dataset) -------------------------------
#
# Used only when *creating* a new template from a RepDB entry, to fill the
# app's own fixed-vocabulary filter columns (muscle_group_id / equipment /
# tracking_type), which RepDB doesn't provide. RepDB's own muscle, image and
# text data is stored as-is and never goes through these tables.

# RepDB body_part -> this app's MuscleGroup.name (cardio/stretching are
# categories in RepDB, handled in muscle_group_name_for_repdb)
REPDB_BODY_PART_TO_MUSCLE_GROUP = {
    "chest": "Chest",
    "back": "Back",
    "shoulders": "Shoulders",
    "core": "Core",
    "upper_arms": "Arms",
    "lower_arms": "Arms",
    "upper_legs": "Legs",
    "lower_legs": "Legs",
    "full_body": "Full Body",
}

# RepDB equipment slug -> this app's EQUIPMENT_TYPES enum. Missing/None means
# bodyweight (RepDB omits `equipment` for bodyweight-only moves).
REPDB_EQUIPMENT_TO_TYPE = {
    "barbell": "barbell",
    "ez_bar": "barbell",
    "trap_bar": "barbell",
    "dumbbell": "dumbbell",
    "kettlebell": "kettlebell",
    "cable": "cable",
    "pull_up_bar": "bodyweight",
    "dip_station": "bodyweight",
    "rings": "bodyweight",
    "suspension_trainer": "bodyweight",
    "ab_crunch_machine": "machine",
    "air_bike": "machine",
    "assisted_pullup_machine": "machine",
    "back_extension_machine": "machine",
    "bicep_curl_machine": "machine",
    "chest_fly_machine": "machine",
    "chest_press_machine": "machine",
    "dip_machine": "machine",
    "donkey_calf_raise_machine": "machine",
    "elliptical": "machine",
    "glute_ham_developer": "machine",
    "hack_squat": "machine",
    "hip_abduction_machine": "machine",
    "hip_adduction_machine": "machine",
    "hip_thrust_machine": "machine",
    "lat_pulldown_machine": "machine",
    "leg_curl": "machine",
    "leg_extension": "machine",
    "leg_press": "machine",
    "pec_deck": "machine",
    "plate_loaded_lateral_raise_machine": "machine",
    "preacher_curl_machine": "machine",
    "rower": "machine",
    "seated_calf_raise_machine": "machine",
    "shoulder_press_machine": "machine",
    "shrug_machine": "machine",
    "ski_erg": "machine",
    "smith_machine": "machine",
    "stair_climber": "machine",
    "standing_calf_raise_machine": "machine",
    "stationary_bike": "machine",
    "treadmill": "machine",
    "tricep_extension_machine": "machine",
    "ab_wheel": "other",
    "battle_rope": "other",
    "climbing_rope": "other",
    "flat_bench": "other",
    "jump_rope": "other",
    "loop_band": "other",
    "plates": "other",
    "plyo_box": "other",
    "resistance_band": "other",
    "slam_ball": "other",
    "sled": "other",
    "stability_ball": "other",
    "wrist_roller": "other",
}


def muscle_group_name_for_repdb(category: str | None, body_part: str | None) -> str | None:
    if category == "cardio":
        return "Cardio"
    if category == "stretching":
        return "Mobility"
    return REPDB_BODY_PART_TO_MUSCLE_GROUP.get((body_part or "").lower())


def equipment_type_for_repdb(equipment: str | None) -> str:
    if not equipment:
        return "bodyweight"
    return REPDB_EQUIPMENT_TO_TYPE.get(equipment.lower(), "other")


def tracking_type_for_repdb(item: dict) -> str:
    if item.get("category") == "cardio":
        return "cardio"
    if item.get("category") == "stretching" or item.get("force_type") == "static":
        return "time"
    if item.get("is_bodyweight"):
        return "bodyweight_reps"
    return "weight_reps"
