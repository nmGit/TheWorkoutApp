"""Resolving which exercise a request body means: a catalog one (`exercise_id`) or the user's
own custom one (`custom_exercise_id`) -- see ExerciseReferenceMixin. A bare id alone is
ambiguous (each table has its own independent id sequence, so a catalog exercise and a custom
one can share the same id), so an API request must say which kind it means, not just supply a
number.
"""

from app.extensions import db
from app.models.exercise_template import CustomExerciseTemplate, ExerciseTemplate
from app.validation import ApiError


def resolve_exercise_reference(body: dict) -> tuple[int | None, int | None]:
    """`(exercise_id, custom_exercise_id)` from a request body that gave exactly one of the
    two, validated to actually exist. Raises ApiError (400/404) otherwise."""
    exercise_id = body.get("exercise_id")
    custom_exercise_id = body.get("custom_exercise_id")
    if bool(exercise_id) == bool(custom_exercise_id):
        raise ApiError("Specify exactly one of exercise_id or custom_exercise_id")
    if exercise_id is not None:
        if db.session.get(ExerciseTemplate, exercise_id) is None:
            raise ApiError(f"Unknown exercise_id {exercise_id}", 404)
        return exercise_id, None
    if db.session.get(CustomExerciseTemplate, custom_exercise_id) is None:
        raise ApiError(f"Unknown custom_exercise_id {custom_exercise_id}", 404)
    return None, custom_exercise_id
