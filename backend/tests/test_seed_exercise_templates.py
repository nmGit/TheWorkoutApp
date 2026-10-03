import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from scripts import seed_exercise_templates as seed_mod
from scripts.seed_exercise_templates import name_tokens, seed

GROUPS = ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Full Body", "Cardio", "Mobility"]


def _legacy(id_, name, **over):
    rec = {
        "id": id_, "name": name, "category": "strength", "body_part": "back",
        "equipment": "dumbbell", "target": "upper back", "muscle_group": "biceps",
        "secondary_muscles": ["biceps", "forearms"],
        "instructions": {"en": f"Do {name}."}, "instruction_steps": {"en": [f"Do {name}."]},
        "image": f"images/{id_}.jpg", "attribution": "© Gym visual — https://gymvisual.com/",
    }
    rec.update(over)
    return rec


def _repdb(id_, name, **over):
    rec = {
        "id": id_, "name_en": name, "category": "strength", "force_type": "pull",
        "mechanic": "compound", "difficulty": "intermediate", "equipment": "dumbbell",
        "body_part": "back", "primary_muscles": ["latissimus_dorsi"],
        "secondary_muscles": ["biceps_brachii"], "is_bodyweight": False,
        "instructions_en": ["Hinge.", "Row."], "tips_en": ["Flat back."],
        "images": {"flat": {"start": f"images/flat/{id_}-start.webp", "peak": f"images/flat/{id_}-peak.webp"}},
    }
    rec.update(over)
    return rec


@pytest.fixture()
def datasets(app, tmp_path, monkeypatch):
    """Tiny fake legacy + RepDB datasets, curated list and mapping, wired
    into the app config / script module constants."""
    legacy_dir, repdb_dir = tmp_path / "legacy", tmp_path / "repdb"
    (legacy_dir / "data").mkdir(parents=True)
    repdb_dir.mkdir()
    curated = tmp_path / "curated.json"
    mapping = tmp_path / "mapping.json"

    def write(legacy=(), repdb=(), curated_exercises=(), name_to_repdb_id=None):
        (legacy_dir / "data" / "exercises.json").write_text(json.dumps(list(legacy)))
        (repdb_dir / "exercises.json").write_text(json.dumps({"exercises": list(repdb)}))
        curated.write_text(json.dumps({"muscle_groups": GROUPS, "exercises": list(curated_exercises)}))
        mapping.write_text(json.dumps({"name_to_repdb_id": name_to_repdb_id or {}}))

    app.config["EXERCISE_DATASET_DIR"] = str(legacy_dir)
    app.config["REPDB_DATASET_DIR"] = str(repdb_dir)
    monkeypatch.setattr(seed_mod, "CURATED_FILE", str(curated))
    monkeypatch.setattr(seed_mod, "REPDB_MAPPING_FILE", str(mapping))
    write()
    return SimpleNamespace(write=write, legacy_dir=legacy_dir, repdb_dir=repdb_dir)


def _by_name(name):
    return ExerciseTemplate.query.filter_by(name=name).one()


def test_name_tokens_is_order_hyphen_and_plural_insensitive():
    assert name_tokens("dumbbell bent over row") == name_tokens("Bent-Over Dumbbell Row")
    assert name_tokens("Chest Dip") == name_tokens("Chest Dips")
    assert name_tokens("Barbell Press") != name_tokens("Dumbbell Press")


def test_seed_creates_legacy_and_repdb_templates(app, datasets):
    datasets.write(
        legacy=[_legacy("0001", "mystery move")],
        repdb=[
            _repdb("plank", "Plank", force_type="static", is_bodyweight=True, equipment=None,
                   body_part="core", images={"flat": {"main": "images/flat/plank-main.webp"}}),
            _repdb("treadmill-running", "Treadmill Running", category="cardio",
                   equipment="treadmill", body_part="full_body", is_bodyweight=False),
        ],
    )
    summary = seed(app)
    assert (summary["legacy_created"], summary["repdb_created"]) == (1, 2)

    legacy = _by_name("mystery move")
    assert legacy.external_id == "0001" and legacy.repdb_id is None
    assert legacy.image_path == "images/0001.jpg"
    assert legacy.primary_muscles == ["upper back"]          # exactly as the source gave it
    assert legacy.secondary_muscles == ["biceps", "forearms"]

    plank = _by_name("Plank")
    assert plank.repdb_images == ["images/flat/plank-main.webp"]
    assert plank.equipment == "bodyweight" and plank.tracking_type == "time"
    assert plank.app_muscle_group.name == "Core"
    assert plank.tips == ["Flat back."] and plank.difficulty == "intermediate"
    assert "repdb.co" in plank.attribution

    treadmill = _by_name("Treadmill Running")
    assert (treadmill.tracking_type, treadmill.equipment) == ("cardio", "machine")
    assert treadmill.app_muscle_group.name == "Cardio"


def test_seed_is_idempotent(app, datasets):
    datasets.write(legacy=[_legacy("0001", "mystery move")], repdb=[_repdb("a-move", "A Move")])
    seed(app)
    before = [(t.id, t.name, t.repdb_id, t.repdb_images, t.tips) for t in ExerciseTemplate.query.order_by("id")]
    summary = seed(app)
    after = [(t.id, t.name, t.repdb_id, t.repdb_images, t.tips) for t in ExerciseTemplate.query.order_by("id")]
    assert before == after
    assert summary["legacy_created"] == summary["repdb_created"] == 0


def test_reseed_never_overwrites_user_editable_fields(app, datasets):
    # The bug this guards against: a re-run used to reset an edited name,
    # equipment, tracking type and muscle group back to the dataset's values.
    datasets.write(
        legacy=[_legacy("0001", "barbell bench press", equipment="barbell", body_part="chest")],
        repdb=[_repdb("bench-press", "Barbell Bench Press", equipment="barbell", body_part="chest")],
    )
    seed(app)
    template = ExerciseTemplate.query.filter_by(external_id="0001").one()
    assert template.repdb_id == "bench-press"
    template.name = "Bench Press"
    template.equipment = "other"
    template.tracking_type = "time"
    template.muscle_group_id = None
    template.notes = "pause at the chest"
    db.session.commit()

    # ...but dataset-owned fields do follow dataset updates.
    datasets.write(
        legacy=[_legacy("0001", "barbell bench press", equipment="barbell", body_part="chest")],
        repdb=[_repdb("bench-press", "Barbell Bench Press", tips_en=["New cue."], equipment="barbell", body_part="chest")],
    )
    seed(app)
    db.session.refresh(template)
    assert (template.name, template.equipment, template.tracking_type) == ("Bench Press", "other", "time")
    assert template.muscle_group_id is None and template.notes == "pause at the chest"
    assert template.tips == ["New cue."]
    assert ExerciseTemplate.query.count() == 1


def test_mapping_claims_a_renamed_template_and_replaces_legacy_content(app, datasets):
    legacy = [_legacy("0001", "dumbbell fly", equipment="dumbbell")]
    datasets.write(legacy=legacy)
    seed(app)
    template = ExerciseTemplate.query.filter_by(external_id="0001").one()
    template.name = "Chest Fly (Dumbbell)"    # the user's own wording: word-set matching can't find it
    db.session.commit()

    datasets.write(
        legacy=legacy,
        repdb=[_repdb("db-fly", "Dumbbell Fly", primary_muscles=["pectoralis_major"], secondary_muscles=["anterior_deltoid"])],
        name_to_repdb_id={"Chest Fly (Dumbbell)": "db-fly"},
    )
    summary = seed(app)
    db.session.refresh(template)
    assert summary["repdb_claimed_mapping"] == 1 and summary["repdb_claimed_wordset"] == 0
    assert template.repdb_id == "db-fly" and template.name == "Chest Fly (Dumbbell)"
    assert template.repdb_images and template.image_path == "images/0001.jpg"   # legacy kept as fallback
    assert template.primary_muscles == ["pectoralis_major"]                      # RepDB's replace legacy
    assert template.secondary_muscles == ["anterior_deltoid"]
    assert "repdb.co" in template.attribution
    assert ExerciseTemplate.query.count() == 1                                   # nothing duplicated


def test_mapping_null_blocks_wordset_match_and_is_reported(app, datasets):
    datasets.write(
        legacy=[_legacy("0001", "barbell hack squat")],
        repdb=[_repdb("hack-squat", "Barbell Hack Squat")],
        name_to_repdb_id={"barbell hack squat": None},
    )
    summary = seed(app)
    template = ExerciseTemplate.query.filter_by(external_id="0001").one()
    assert template.repdb_id is None                      # blocked by the null entry
    assert summary["repdb_created"] == 1                  # RepDB's entry became its own template
    assert summary["possible_duplicates"]                 # ...and is flagged for human review


def test_slug_can_be_claimed_by_only_one_template(app, datasets):
    datasets.write(
        legacy=[_legacy("0001", "barbell bench press"), _legacy("0002", "bench press barbell")],
        repdb=[_repdb("bench-press", "Barbell Bench Press")],
    )
    summary = seed(app)
    claimed = ExerciseTemplate.query.filter_by(repdb_id="bench-press").all()
    assert len(claimed) == 1
    assert len(summary["collisions"]) == 1


def test_dry_run_writes_nothing(app, datasets):
    datasets.write(legacy=[_legacy("0001", "mystery move")], repdb=[_repdb("a-move", "A Move")])
    summary = seed(app, dry_run=True)
    assert summary["legacy_created"] == 1 and summary["repdb_created"] == 1
    assert ExerciseTemplate.query.count() == 0


def test_curated_overrides_apply_only_to_rows_created_in_this_run(app, datasets):
    curated = [{"name": "dumbbell squat", "muscle_group": "Legs", "equipment": "kettlebell", "tracking_type": "bodyweight_reps"}]
    datasets.write(legacy=[_legacy("0001", "dumbbell squat", body_part="upper legs")], curated_exercises=curated)
    seed(app)
    template = ExerciseTemplate.query.filter_by(external_id="0001").one()
    assert (template.equipment, template.tracking_type) == ("kettlebell", "bodyweight_reps")

    template.equipment = "dumbbell"
    db.session.commit()
    seed(app)                                              # now an existing row: hands off
    db.session.refresh(template)
    assert template.equipment == "dumbbell"
    assert ExerciseTemplate.query.count() == 1


def test_curated_creates_missing_custom_exercise_on_fresh_install(app, datasets):
    curated = [{"name": "My Own Move", "muscle_group": "Core", "equipment": "bodyweight", "tracking_type": "bodyweight_reps"}]
    datasets.write(curated_exercises=curated)
    summary = seed(app)
    template = _by_name("My Own Move")
    assert template.is_custom and template.external_id is None and summary["curated_created"] == 1
