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


def equipment_type_for(equipment: str | None) -> str:
    if not equipment:
        return "other"
    return EQUIPMENT_TO_TYPE.get(equipment.lower(), "other")
