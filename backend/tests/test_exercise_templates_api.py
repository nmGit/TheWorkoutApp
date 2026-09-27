from app.extensions import db
from app.models.exercise_template import ExerciseTemplate


def _make_template(**overrides):
    defaults = dict(
        external_id="0001",
        name="3/4 sit-up",
        category="waist",
        body_part="waist",
        equipment="body weight",
        target_muscle="abs",
        muscle_group="hip flexors",
        secondary_muscles=["hip flexors", "lower back"],
        instructions="Lie flat on your back...",
        instruction_steps=["Lie flat on your back...", "Curl up."],
        image_path="images/0001-2gPfomN.jpg",
        attribution="© Gym visual — https://gymvisual.com/",
        is_custom=False,
    )
    defaults.update(overrides)
    template = ExerciseTemplate(**defaults)
    db.session.add(template)
    db.session.commit()
    return template


def test_list_exercise_templates_search_and_pagination(client, app):
    with app.app_context():
        _make_template(external_id="0001", name="3/4 sit-up")
        _make_template(external_id="0002", name="45 degree side bend", body_part="waist")

    resp = client.get("/api/exercise-templates?q=sit-up")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "3/4 sit-up"
    assert body["items"][0]["image_url"] == f"/api/exercise-templates/{body['items'][0]['id']}/image"
    assert body["items"][0]["instruction_steps"] == ["Lie flat on your back...", "Curl up."]


def test_exercise_template_facets(client, app):
    with app.app_context():
        _make_template(external_id="0001", body_part="waist", equipment="body weight")
        _make_template(external_id="0002", body_part="chest", equipment="barbell")

    resp = client.get("/api/exercise-templates/facets")
    body = resp.get_json()
    assert set(body["body_parts"]) == {"waist", "chest"}
    assert set(body["equipment"]) == {"body weight", "barbell"}


def test_exercise_template_image_404_when_missing(client, app):
    with app.app_context():
        template = _make_template(external_id="0001", image_path=None)
        template_id = template.id

    resp = client.get(f"/api/exercise-templates/{template_id}/image")
    assert resp.status_code == 404


def test_create_exercise_from_dataset_template_derives_fields(client, app):
    with app.app_context():
        from app.models.exercise import MuscleGroup

        db.session.add(MuscleGroup(name="Core", display_order=0))
        db.session.commit()
        template = _make_template(
            external_id="0001",
            name="3/4 sit-up",
            body_part="waist",
            equipment="body weight",
        )
        template_id = template.id

    resp = client.post("/api/exercises", json={"template_id": template_id})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "3/4 sit-up"
    assert body["muscle_group_name"] == "Core"
    assert body["equipment"] == "bodyweight"
    assert body["is_custom"] is False
    assert body["template_id"] == template_id
    assert body["template"]["instruction_steps"] == ["Lie flat on your back...", "Curl up."]
    assert body["template"]["image_url"] == f"/api/exercise-templates/{template_id}/image"
    assert body["template"]["attribution"] == "© Gym visual — https://gymvisual.com/"


def test_create_exercise_from_unknown_template_404s(client, chest_group):
    resp = client.post("/api/exercises", json={"template_id": 999, "muscle_group_id": chest_group.id})
    assert resp.status_code == 404


def test_create_custom_exercise_auto_creates_template(client, chest_group):
    resp = client.post(
        "/api/exercises",
        json={"name": "Cable Crossover", "muscle_group_id": chest_group.id, "tracking_type": "weight_reps"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["is_custom"] is True
    assert body["template_id"] is not None
    assert body["template"]["is_custom"] is True
    assert body["template"]["image_url"] is None

    template = db.session.get(ExerciseTemplate, body["template_id"])
    assert template.name == "Cable Crossover"
    assert template.is_custom is True
