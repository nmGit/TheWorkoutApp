"""Model -> JSON-serializable dict helpers.

Kept separate from the models so response shape can evolve independently
of the ORM mapping (e.g. nesting, computed fields like `last_performed`).
"""
import os
import re
from functools import lru_cache

from flask import current_app


def _num(value):
    return float(value) if value is not None else None


def serialize_muscle_group(mg):
    return {"id": mg.id, "name": mg.name, "display_order": mg.display_order}


@lru_cache(maxsize=8)
def _muscle_image_slugs(dataset_dir: str) -> frozenset:
    """Muscles RepDB ships a highlighted-body diagram for, as underscore
    slugs (the files are dash-named, e.g. images/muscles/pectoralis-major.webp)."""
    try:
        names = os.listdir(os.path.join(dataset_dir, "images", "muscles"))
    except OSError:
        return frozenset()
    return frozenset(n[:-5].replace("-", "_") for n in names if n.endswith(".webp"))


def muscle_slug(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", name.strip().lower())


def _muscle_swatch(name: str) -> dict:
    """A muscle string exactly as its source dataset gave it (RepDB:
    "pectoralis_major"; the original dataset: "pectorals"), plus a diagram
    when RepDB happens to have one under the same name -- no translation
    between the two vocabularies, so coarse legacy terms just get no image."""
    slug = muscle_slug(name)
    has_image = slug in _muscle_image_slugs(current_app.config["REPDB_DATASET_DIR"])
    return {
        "name": re.sub(r"[_\-]+", " ", name).strip().title(),
        "image_url": f"/api/muscles/{slug}/image" if has_image else None,
    }


def image_count(template) -> int:
    """How many images a template has: RepDB's (1-2 poses) win over the
    original dataset's single image."""
    if template.repdb_images:
        return len(template.repdb_images)
    return 1 if template.image_path else 0


def serialize_exercise_template(template, last_performed=None):
    n_images = image_count(template)
    image_urls = [
        f"/api/exercise-templates/{template.id}/image" + ("" if i == 0 else f"/{i}")
        for i in range(n_images)
    ]
    data = {
        "id": template.id,
        "external_id": template.external_id,
        "name": template.name,
        "category": template.category,
        "body_part": template.body_part,
        "equipment": template.equipment,
        "equipment_raw": template.equipment_raw,
        "target_muscle": template.target_muscle,
        "muscle_group": template.muscle_group,
        "muscle_group_id": template.muscle_group_id,
        "muscle_group_name": template.app_muscle_group.name if template.app_muscle_group else None,
        "tracking_type": template.tracking_type,
        "primary_muscles": [_muscle_swatch(m) for m in (template.primary_muscles or [])],
        "secondary_muscles": [_muscle_swatch(m) for m in (template.secondary_muscles or [])],
        "instructions": template.instructions,
        "instruction_steps": template.instruction_steps or [],
        "tips": template.tips or [],
        "difficulty": template.difficulty,
        "mechanic": template.mechanic,
        "image_url": image_urls[0] if image_urls else None,
        "image_urls": image_urls,
        "attribution": template.attribution,
        "notes": template.notes,
        "is_custom": template.is_custom,
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
        "rest_seconds": s.rest_seconds,
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
