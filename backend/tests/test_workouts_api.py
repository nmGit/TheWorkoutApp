from datetime import date, timedelta


def test_start_and_finish_blank_workout(client, bench_press):
    resp = client.post("/api/workouts", json={})
    assert resp.status_code == 201
    workout = resp.get_json()
    assert workout["is_active"] is True

    resp = client.get("/api/workouts/active")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == workout["id"]

    resp = client.post(f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id})
    assert resp.status_code == 201
    we_id = resp.get_json()["exercises"][0]["id"]

    resp = client.post(f"/api/workout-exercises/{we_id}/sets", json={"weight": 135, "weight_unit": "lbs", "reps": 5})
    assert resp.status_code == 201
    set_data = resp.get_json()
    assert set_data["completed"] is False

    resp = client.patch(f"/api/sets/{set_data['id']}", json={"completed": True})
    assert resp.status_code == 200
    assert resp.get_json()["completed"] is True

    resp = client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["completed_at"] is not None
    assert len(body["exercises"][0]["sets"]) == 1  # completed set survives


def test_set_weight_preserves_precision_for_unit_conversion(client, bench_press):
    # Weight columns must hold more than 2 decimal places: values imported
    # from a kg-denominated source (e.g. Strong's CSV export) carry several
    # decimal places, and rounding them off before storage means the
    # kg->lbs display conversion visibly drifts from the true value (e.g.
    # 61.23 kg displays as 134.99 lbs instead of the true 135.00 lbs the
    # lifter actually entered). See docs/data_migration.rst.
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    resp = client.post(
        f"/api/workout-exercises/{we['id']}/sets",
        json={"weight": 61.23492, "weight_unit": "kg", "reps": 5},
    )
    set_id = resp.get_json()["id"]

    fetched = client.get(f"/api/workouts/{workout['id']}").get_json()
    stored_weight = fetched["exercises"][0]["sets"][0]["weight"]
    # 2 dp tolerance: at 1 dp, the old (broken) 2-decimal-place column
    # rounding and today's 4-decimal-place column both happen to round to
    # 135.0, so 1 dp wouldn't actually catch a regression back to it.
    assert round(stored_weight * 2.20462262185, 2) == 135.0


def test_only_one_active_workout(client):
    resp = client.post("/api/workouts", json={})
    assert resp.status_code == 201

    resp = client.post("/api/workouts", json={})
    assert resp.status_code == 409


def test_finish_drops_incomplete_sets(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    client.post(f"/api/workout-exercises/{we['id']}/sets", json={"weight": 100, "reps": 5})

    resp = client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})
    body = resp.get_json()
    assert body["exercises"][0]["sets"] == []


def test_start_from_template(client, bench_press):
    template = client.post(
        "/api/templates",
        json={
            "name": "Push Day",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 3, "target_reps": "8", "target_weight": 135}
            ],
        },
    ).get_json()

    resp = client.post("/api/workouts", json={"template_id": template["id"]})
    assert resp.status_code == 201
    workout = resp.get_json()
    assert workout["name"] == "Push Day"
    sets = workout["exercises"][0]["sets"]
    assert len(sets) == 3
    assert all(s["reps"] == 8 and s["weight"] == 135 and s["completed"] is False for s in sets)


def test_start_from_template_with_rep_range(client, bench_press):
    # target_reps is free-form to allow ranges (see data_model.rst); a range
    # should still pre-fill something rather than silently leaving reps blank.
    template = client.post(
        "/api/templates",
        json={
            "name": "Push Day",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 2, "target_reps": "8-12", "target_weight": 135}
            ],
        },
    ).get_json()

    workout = client.post("/api/workouts", json={"template_id": template["id"]}).get_json()
    sets = workout["exercises"][0]["sets"]
    assert all(s["reps"] == 8 for s in sets)


def test_list_workouts_date_range(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    resp = client.get(f"/api/workouts?start={today}&end={tomorrow}")
    assert len(resp.get_json()) == 1

    resp = client.get(f"/api/workouts?start={tomorrow}")
    assert len(resp.get_json()) == 0

    resp = client.get(f"/api/workouts?end={yesterday}")
    assert len(resp.get_json()) == 0


def test_delete_template_keeps_workout_history(client, bench_press):
    template = client.post("/api/templates", json={"name": "Push Day", "exercises": []}).get_json()
    workout = client.post("/api/workouts", json={"template_id": template["id"]}).get_json()
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    resp = client.delete(f"/api/templates/{template['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/api/workouts/{workout['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["template_id"] is None


def test_cannot_delete_exercise_with_history(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    client.post(f"/api/workout-exercises/{we['id']}/sets", json={"weight": 100, "reps": 5, "completed": True})
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    resp = client.delete(f"/api/exercises/{bench_press.id}")
    assert resp.status_code == 409
