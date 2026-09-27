"""Model -> JSON-serializable dict helpers.

Kept separate from the models so response shape can evolve independently
of the ORM mapping (e.g. nesting, computed fields like `last_performed`).
"""


def _num(value):
    return float(value) if value is not None else None


def serialize_muscle_group(mg):
    return {"id": mg.id, "name": mg.name, "display_order": mg.display_order}


def serialize_exercise(exercise, last_performed=None):
    data = {
        "id": exercise.id,
        "name": exercise.name,
        "muscle_group_id": exercise.muscle_group_id,
        "muscle_group_name": exercise.muscle_group.name if exercise.muscle_group else None,
        "equipment": exercise.equipment,
        "tracking_type": exercise.tracking_type,
        "is_custom": exercise.is_custom,
        "default_rest_seconds": exercise.default_rest_seconds,
        "notes": exercise.notes,
    }
    if last_performed is not None:
        data["last_performed"] = last_performed
    return data


def serialize_template_exercise(te):
    return {
        "id": te.id,
        "exercise_id": te.exercise_id,
        "exercise_name": te.exercise.name if te.exercise else None,
        "position": te.position,
        "target_sets": te.target_sets,
        "target_reps": te.target_reps,
        "target_weight": _num(te.target_weight),
    }


def serialize_template(template, include_exercises=True):
    data = {
        "id": template.id,
        "name": template.name,
        "notes": template.notes,
        "display_order": template.display_order,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }
    if include_exercises:
        data["exercises"] = [serialize_template_exercise(te) for te in template.exercises]
    return data


def serialize_set(s):
    return {
        "id": s.id,
        "position": s.position,
        "weight": _num(s.weight),
        "weight_unit": s.weight_unit,
        "reps": s.reps,
        "duration_seconds": s.duration_seconds,
        "distance_meters": _num(s.distance_meters),
        "is_warmup": s.is_warmup,
        "is_dropset": s.is_dropset,
        "rpe": _num(s.rpe),
        "completed": s.completed,
    }


def serialize_workout_exercise(we, include_sets=True):
    data = {
        "id": we.id,
        "exercise_id": we.exercise_id,
        "exercise_name": we.exercise.name if we.exercise else None,
        "tracking_type": we.exercise.tracking_type if we.exercise else None,
        "position": we.position,
        "notes": we.notes,
    }
    if include_sets:
        data["sets"] = [serialize_set(s) for s in we.sets]
    return data


def serialize_workout(workout, include_exercises=True):
    data = {
        "id": workout.id,
        "name": workout.name,
        "template_id": workout.template_id,
        "template_name": workout.template.name if workout.template else None,
        "started_at": workout.started_at.isoformat() if workout.started_at else None,
        "completed_at": workout.completed_at.isoformat() if workout.completed_at else None,
        "notes": workout.notes,
        "body_weight": _num(workout.body_weight),
        "is_active": workout.is_active,
    }
    if include_exercises:
        data["exercises"] = [
            serialize_workout_exercise(we) for we in workout.exercises
        ]
    else:
        data["exercise_count"] = len(workout.exercises)
    return data


def serialize_bodyweight_entry(entry):
    return {
        "id": entry.id,
        "recorded_at": entry.recorded_at.isoformat() if entry.recorded_at else None,
        "weight": _num(entry.weight),
        "unit": entry.unit,
    }


def serialize_settings(settings):
    return {
        "weight_unit": settings.weight_unit,
        "distance_unit": settings.distance_unit,
        "default_rest_seconds": settings.default_rest_seconds,
        "theme": settings.theme,
    }
