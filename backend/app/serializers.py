"""Model -> JSON-serializable dict helpers.

Kept separate from the models so response shape can evolve independently
of the ORM mapping (e.g. nesting, computed fields like `last_performed`).
"""
import os
import re
from datetime import timezone
from functools import lru_cache

from flask import current_app

from app.services.muscle_regions import regions_for


def _num(value):
    return float(value) if value is not None else None


# A diagram that stands in for each muscle group in the exercise filter chips.
# Groups without a single representative muscle (Full Body, Cardio, Mobility)
# get no image.
GROUP_DIAGRAM_MUSCLE = {
    "Chest": "pectoralis_major",
    "Back": "latissimus_dorsi",
    "Shoulders": "lateral_deltoid",
    "Arms": "biceps_brachii",
    "Core": "rectus_abdominis",
    "Legs": "quadriceps",
}


def _utc_iso(dt):
    """A datetime as ISO 8601 with an explicit UTC offset. Every stored timestamp is
    UTC, but SQLite hands them back naive, and a naive string reads as *local* time in
    a browser -- which put a workout started a few hours ago in the future, so its
    elapsed time sat at 0."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def serialize_muscle_group(mg):
    diagram = GROUP_DIAGRAM_MUSCLE.get(mg.name)
    return {
        "id": mg.id,
        "name": mg.name,
        "display_order": mg.display_order,
        "image_url": muscle_swatch(diagram)["image_url"] if diagram else None,
    }


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


# The original dataset's short spellings for muscles RepDB names in full. Only
# unambiguous ones: "forearms" could mean the flexors, the extensors or both.
MUSCLE_SYNONYMS = {
    "biceps": "biceps_brachii",
    "triceps": "triceps_brachii",
    "traps": "trapezius",
    "glutes": "gluteus_maximus",
    "abs": "rectus_abdominis",
    "abdominals": "rectus_abdominis",
    "pectorals": "pectoralis_major",
    "quads": "quadriceps",
    "lats": "latissimus_dorsi",
    "delts": "deltoids",
    "rear_deltoids": "posterior_deltoid",
    "groin": "adductors",
    "inner_thighs": "adductors",
    "shins": "tibialis",
}

def muscle_display_name(name: str) -> str:
    return re.sub(r"[_\-]+", " ", name).strip().title()


def canonical_muscle_slug(name: str) -> str:
    """The key a muscle is known by across both datasets: "biceps" and
    "biceps_brachii" are the same muscle. The exercise library filters on this."""
    slug = muscle_slug(name)
    return MUSCLE_SYNONYMS.get(slug, slug)


def muscle_swatch(name: str) -> dict:
    """A muscle as the app shows it: its canonical slug and display name, plus a
    diagram when RepDB has one for it."""
    slug = canonical_muscle_slug(name)
    has_image = slug in _muscle_image_slugs(current_app.config["REPDB_DATASET_DIR"])
    return {
        "slug": slug,
        "name": muscle_display_name(slug),
        "image_url": f"/api/muscles/{slug}/image" if has_image else None,
        "regions": regions_for(slug),
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
        "primary_muscles": [muscle_swatch(m) for m in (template.primary_muscles or [])],
        "secondary_muscles": [muscle_swatch(m) for m in (template.secondary_muscles or [])],
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
        "warmup_sets": te.warmup_sets,
        "drop_sets": te.drop_sets,
        "target_reps": te.target_reps,
        "target_weight": _num(te.target_weight),
    }


def muscle_summary(exercise_templates) -> dict:
    """The muscles a set of exercises works, as canonical slugs: `primary` (worked
    mainly by at least one exercise) and `secondary` (incidental, and not already
    primary), plus the names of the muscle groups they belong to, in the app's
    group order. Exercises not yet linked to a template are skipped."""
    primary, secondary, groups = set(), set(), {}
    for ex in exercise_templates:
        if ex is None:
            continue
        primary.update(canonical_muscle_slug(m) for m in ex.primary_muscles or [])
        secondary.update(canonical_muscle_slug(m) for m in ex.secondary_muscles or [])
        if ex.app_muscle_group is not None:
            groups[ex.app_muscle_group.name] = ex.app_muscle_group.display_order
    return {
        "primary": sorted(primary),
        "secondary": sorted(secondary - primary),
        "groups": sorted(groups, key=lambda name: groups[name]),
        "regions": sorted({r for slug in primary | secondary for r in regions_for(slug)}),
    }


def serialize_template(template, include_exercises=True):
    data = {
        "id": template.id,
        "name": template.name,
        "notes": template.notes,
        "display_order": template.display_order,
        "created_at": _utc_iso(template.created_at),
        "updated_at": _utc_iso(template.updated_at),
    }
    data["muscles"] = muscle_summary(te.exercise for te in template.exercises)
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
        "planned_weight": _num(s.planned_weight),
        "planned_weight_unit": s.planned_weight_unit,
        "planned_reps": s.planned_reps,
        "planned_duration_seconds": s.planned_duration_seconds,
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
        "started_at": _utc_iso(workout.started_at),
        "completed_at": _utc_iso(workout.completed_at),
        "notes": workout.notes,
        "body_weight": _num(workout.body_weight),
        "is_active": workout.is_active,
        "muscles": muscle_summary(we.exercise for we in workout.exercises),
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
        "progression_method": settings.progression_method,
        "experience": settings.experience,
        "load_step_lb": settings.load_step_lb,
        "load_step_kg": settings.load_step_kg,
        "default_rep_range": settings.default_rep_range,
    }
