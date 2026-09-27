def test_settings_roundtrip(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    assert resp.get_json()["weight_unit"] == "lbs"

    resp = client.patch("/api/settings", json={"weight_unit": "kg", "default_rest_seconds": 120})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["weight_unit"] == "kg"
    assert body["default_rest_seconds"] == 120


def test_settings_rejects_invalid_unit(client):
    resp = client.patch("/api/settings", json={"weight_unit": "stone"})
    assert resp.status_code == 400


def test_bodyweight_upsert_one_per_day(client):
    resp = client.post("/api/bodyweight", json={"weight": 180, "recorded_at": "2024-01-01", "unit": "lbs"})
    assert resp.status_code == 201
    entry_id = resp.get_json()["id"]

    resp = client.post("/api/bodyweight", json={"weight": 181, "recorded_at": "2024-01-01", "unit": "lbs"})
    assert resp.status_code == 201
    assert resp.get_json()["id"] == entry_id
    assert resp.get_json()["weight"] == 181.0

    resp = client.get("/api/bodyweight")
    assert len(resp.get_json()) == 1


def test_create_custom_exercise_and_list_filter(client, chest_group):
    resp = client.post(
        "/api/exercises",
        json={"name": "Cable Crossover", "muscle_group_id": chest_group.id, "tracking_type": "weight_reps"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["is_custom"] is True

    resp = client.get(f"/api/exercises?muscle_group_id={chest_group.id}")
    names = [e["name"] for e in resp.get_json()]
    assert "Cable Crossover" in names


def test_create_exercise_rejects_bad_tracking_type(client, chest_group):
    resp = client.post(
        "/api/exercises",
        json={"name": "X", "muscle_group_id": chest_group.id, "tracking_type": "not_a_type"},
    )
    assert resp.status_code == 400


def test_dashboard_recent_prs(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    client.post(
        f"/api/workout-exercises/{we['id']}/sets",
        json={"weight": 200, "weight_unit": "lbs", "reps": 5, "completed": True},
    )
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    resp = client.get("/api/stats/dashboard")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["active_workout_id"] is None
    assert body["current_streak_weeks"] >= 1
    metrics = {pr["metric"] for pr in body["recent_prs"]}
    assert "max_weight" in metrics


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

    resp = client.get(f"/api/exercises/{bench_press.id}/history")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1

    resp = client.get(f"/api/exercises/{bench_press.id}/stats")
    body = resp.get_json()
    assert body["personal_records"]["max_weight"]["value"] == 135.0
    assert len(body["series"]) == 1
