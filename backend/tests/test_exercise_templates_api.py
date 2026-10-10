import pytest

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate


def _make_template(**overrides):
    defaults = dict(
        external_id="0001",
        name="3/4 sit-up",
        category="waist",
        body_part="waist",
        equipment="bodyweight",
        equipment_raw="body weight",
        target_muscle="abs",
        muscle_group="hip flexors",
        secondary_muscles=["hip flexors", "lower back"],
        instructions="Lie flat on your back...",
        instruction_steps=["Lie flat on your back...", "Curl up."],
        image_path="images/0001-2gPfomN.jpg",
        attribution="© Gym visual — https://gymvisual.com/",
        tracking_type="weight_reps",
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


def test_list_exercise_templates_filters_by_muscle_group_id(client, app, chest_group):
    with app.app_context():
        _make_template(external_id="0001", name="barbell bench press", muscle_group_id=chest_group.id)
        _make_template(external_id="0002", name="barbell squat", muscle_group_id=None)

    resp = client.get(f"/api/exercise-templates?muscle_group_id={chest_group.id}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "barbell bench press"
    assert body["items"][0]["muscle_group_name"] == "Chest"


def test_list_exercise_templates_muscle_group_filter_includes_custom_templates(client, app, chest_group):
    # Before muscle_group_id existed as a real column, custom templates had
    # no way to be found by muscle-group filter at all (they had no
    # body_part, the dataset-only field the filter used to check) -- see
    # docs/source/review.rst. Now both custom and dataset-sourced templates
    # just use the same real column.
    with app.app_context():
        _make_template(external_id="0001", name="barbell bench press", muscle_group_id=chest_group.id)
        _make_template(
            external_id=None, name="Cable Crossover", muscle_group_id=chest_group.id, is_custom=True
        )

    resp = client.get(f"/api/exercise-templates?muscle_group_id={chest_group.id}")
    body = resp.get_json()
    names = {t["name"] for t in body["items"]}
    assert names == {"barbell bench press", "Cable Crossover"}


def test_list_exercise_templates_unknown_muscle_group_404s(client):
    resp = client.get("/api/exercise-templates?muscle_group_id=999")
    assert resp.status_code == 404


def test_exercise_template_facets(client, app):
    with app.app_context():
        _make_template(external_id="0001", body_part="waist", equipment_raw="body weight")
        _make_template(external_id="0002", body_part="chest", equipment_raw="barbell")

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


def test_create_custom_exercise_template(client, chest_group):
    resp = client.post(
        "/api/exercise-templates",
        json={"name": "Cable Crossover", "muscle_group_id": chest_group.id, "tracking_type": "weight_reps"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["is_custom"] is True
    assert body["muscle_group_name"] == "Chest"
    assert body["image_url"] is None

    template = db.session.get(ExerciseTemplate, body["id"])
    assert template.name == "Cable Crossover"
    assert template.is_custom is True


def test_create_exercise_template_rejects_bad_tracking_type(client, chest_group):
    resp = client.post(
        "/api/exercise-templates",
        json={"name": "X", "muscle_group_id": chest_group.id, "tracking_type": "not_a_type"},
    )
    assert resp.status_code == 400


def test_create_exercise_template_and_list_filter(client, chest_group):
    resp = client.post(
        "/api/exercise-templates",
        json={"name": "Cable Crossover", "muscle_group_id": chest_group.id, "tracking_type": "weight_reps"},
    )
    assert resp.status_code == 201

    resp = client.get(f"/api/exercise-templates?muscle_group_id={chest_group.id}")
    names = [e["name"] for e in resp.get_json()["items"]]
    assert "Cable Crossover" in names


def test_update_exercise_template(client, bench_press):
    resp = client.patch(f"/api/exercise-templates/{bench_press.id}", json={"notes": "Grip just outside shoulder width"})
    assert resp.status_code == 200
    assert resp.get_json()["notes"] == "Grip just outside shoulder width"


def test_cannot_delete_dataset_sourced_template(client, app):
    with app.app_context():
        template = _make_template(external_id="0001", is_custom=False)
        template_id = template.id

    resp = client.delete(f"/api/exercise-templates/{template_id}")
    assert resp.status_code == 409


def test_delete_unused_custom_template(client, chest_group):
    created = client.post(
        "/api/exercise-templates",
        json={"name": "Cable Crossover", "muscle_group_id": chest_group.id},
    ).get_json()

    resp = client.delete(f"/api/exercise-templates/{created['id']}")
    assert resp.status_code == 204


def test_exercise_history_and_stats(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    client.post(
        f"/api/workout-exercises/{we['id']}/sets",
        json={"weight": 135, "weight_unit": "lbs", "reps": 5, "completed": True},
    )
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    resp = client.get(f"/api/exercise-templates/{bench_press.id}/history")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1

    resp = client.get(f"/api/exercises/{bench_press.id}/stats")
    body = resp.get_json()
    assert body["personal_records"]["max_weight"]["value"] == 135.0
    assert len(body["series"]) == 1


# --- images (RepDB poses with legacy fallback) and muscle swatches ---------

WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF"


@pytest.fixture()
def dataset_files(app, tmp_path):
    legacy, repdb = tmp_path / "legacy", tmp_path / "repdb"
    for path, data in [
        (legacy / "images" / "0001.jpg", JPEG),
        (repdb / "images" / "flat" / "a-start.webp", WEBP),
        (repdb / "images" / "flat" / "a-peak.webp", WEBP),
        (repdb / "images" / "muscles" / "pectoralis-major.webp", WEBP),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    app.config["EXERCISE_DATASET_DIR"] = str(legacy)
    app.config["REPDB_DATASET_DIR"] = str(repdb)
    return tmp_path


def test_repdb_poses_are_served_as_webp_and_listed(client, app, dataset_files):
    with app.app_context():
        template = _make_template(
            repdb_images=["images/flat/a-start.webp", "images/flat/a-peak.webp"],
            image_path="images/0001.jpg",
        )
        template_id = template.id

    detail = client.get(f"/api/exercise-templates/{template_id}").get_json()
    assert detail["image_urls"] == [
        f"/api/exercise-templates/{template_id}/image",
        f"/api/exercise-templates/{template_id}/image/1",
    ]
    assert detail["image_url"] == detail["image_urls"][0]

    for url in detail["image_urls"]:
        resp = client.get(url)
        assert resp.status_code == 200 and resp.mimetype == "image/webp"
        assert "max-age" in resp.headers["Cache-Control"]
    assert client.get(f"/api/exercise-templates/{template_id}/image/2").status_code == 404


def test_legacy_image_is_the_fallback_when_repdb_has_none(client, app, dataset_files):
    with app.app_context():
        template_id = _make_template(image_path="images/0001.jpg").id
    detail = client.get(f"/api/exercise-templates/{template_id}").get_json()
    assert len(detail["image_urls"]) == 1
    resp = client.get(detail["image_url"])
    assert resp.status_code == 200 and resp.mimetype == "image/jpeg"
    assert client.get(f"/api/exercise-templates/{template_id}/image/1").status_code == 404


def test_missing_repdb_file_falls_back_to_legacy_image(client, app, dataset_files):
    with app.app_context():
        template_id = _make_template(
            repdb_images=["images/flat/not-there.webp"], image_path="images/0001.jpg"
        ).id
    resp = client.get(f"/api/exercise-templates/{template_id}/image")
    assert resp.status_code == 200 and resp.mimetype == "image/jpeg"


def test_image_path_traversal_is_rejected(client, app, dataset_files):
    with app.app_context():
        template_id = _make_template(
            repdb_images=["../legacy/images/0001.jpg"], image_path=None
        ).id
    assert client.get(f"/api/exercise-templates/{template_id}/image").status_code == 404


def test_template_without_any_image_has_no_urls(client, app, dataset_files):
    with app.app_context():
        template_id = _make_template(image_path=None).id
    detail = client.get(f"/api/exercise-templates/{template_id}").get_json()
    assert detail["image_url"] is None and detail["image_urls"] == []


def test_muscle_swatches_link_an_image_only_when_repdb_has_one(client, app, dataset_files):
    with app.app_context():
        template_id = _make_template(
            primary_muscles=["pectoralis_major"],
            secondary_muscles=["pectorals", "Upper Back"],
            tips=["Keep your feet flat."],
            difficulty="beginner",
            mechanic="compound",
        ).id
    detail = client.get(f"/api/exercise-templates/{template_id}").get_json()
    # The legacy "pectorals" is the same muscle as the primary pectoralis_major, so it isn't
    # listed twice. "Upper Back" is a separate muscle.
    assert detail["primary_muscles"] == [
        {
            "slug": "pectoralis_major",
            "name": "Pectoralis Major",
            "image_url": "/api/muscles/pectoralis_major/image",
            "regions": ["chest"],
        }
    ]
    assert detail["secondary_muscles"] == [
        {"slug": "upper_back", "name": "Upper Back", "image_url": None, "regions": ["upper-back"]},
    ]
    assert detail["tips"] == ["Keep your feet flat."]
    assert (detail["difficulty"], detail["mechanic"]) == ("beginner", "compound")


def test_muscle_image_route(client, dataset_files):
    resp = client.get("/api/muscles/pectoralis_major/image")
    assert resp.status_code == 200 and resp.mimetype == "image/webp"
    assert client.get("/api/muscles/biceps_brachii/image").status_code == 404   # no such file
    assert client.get("/api/muscles/Bad.Slug/image").status_code == 404         # not a valid slug


def test_template_with_no_muscle_data_serializes_empty_lists(client, app, dataset_files):
    with app.app_context():
        template_id = _make_template(secondary_muscles=None).id
    detail = client.get(f"/api/exercise-templates/{template_id}").get_json()
    assert detail["primary_muscles"] == [] and detail["secondary_muscles"] == []
    assert detail["tips"] == []
