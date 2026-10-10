from datetime import date, timedelta

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate


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


def test_start_from_template_makes_the_planned_sets(client, bench_press):
    """The template sets how many sets of each kind start the workout. With no earlier session,
    the values are empty."""
    template = client.post(
        "/api/templates",
        json={
            "name": "Push Day",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 3, "warmup_sets": 1, "drop_sets": 1}
            ],
        },
    ).get_json()

    resp = client.post("/api/workouts", json={"template_id": template["id"]})
    assert resp.status_code == 201
    workout = resp.get_json()
    assert workout["name"] == "Push Day"
    sets = workout["exercises"][0]["sets"]
    assert [(s["is_warmup"], s["is_dropset"]) for s in sets] == [
        (True, False), (False, False), (False, False), (False, False), (False, True),
    ]
    assert all(s["weight"] is None and s["reps"] is None and s["completed"] is False for s in sets)


def test_start_from_template_copies_values_from_the_last_session(client, bench_press):
    """Weight and reps come from the last completed session of the exercise, not the template."""
    template = client.post(
        "/api/templates",
        json={"name": "Push Day", "exercises": [{"exercise_id": bench_press.id, "target_sets": 3}]},
    ).get_json()

    earlier = client.post("/api/workouts", json={}).get_json()
    we = client.post(f"/api/workouts/{earlier['id']}/exercises", json={"exercise_id": bench_press.id}).get_json()
    we_id = we["exercises"][0]["id"]
    set_id = client.post(f"/api/workout-exercises/{we_id}/sets", json={}).get_json()["id"]
    client.patch(f"/api/sets/{set_id}", json={"weight": 135, "weight_unit": "lbs", "reps": 8, "completed": True})
    client.patch(f"/api/workouts/{earlier['id']}", json={"finish": True})

    workout = client.post("/api/workouts", json={"template_id": template["id"]}).get_json()
    sets = workout["exercises"][0]["sets"]
    assert len(sets) == 3
    # Double progression with the default 8-12 range: 8 reps is below the top, so add a rep.
    assert all(s["weight"] is None and s["planned_weight"] == 135 and s["planned_reps"] == 9 for s in sets)


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


def test_new_sets_do_not_copy_rest_seconds(client, bench_press):
    # Unlike weight, a new set's rest starts empty: the UI shows ghost text
    # derived from the sets before it (and last time), so editing one set's
    # rest carries forward to the sets after it instead of each new set
    # freezing its own copy.
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]

    first = client.post(
        f"/api/workout-exercises/{we['id']}/sets", json={"weight": 135, "reps": 5, "rest_seconds": 90}
    ).get_json()
    assert first["rest_seconds"] == 90                      # explicit values are stored

    second = client.post(f"/api/workout-exercises/{we['id']}/sets", json={}).get_json()
    assert second["weight"] == 135 and second["rest_seconds"] is None

    resp = client.patch(f"/api/sets/{second['id']}", json={"rest_seconds": 120, "completed": True})
    assert resp.get_json()["rest_seconds"] == 120 and resp.get_json()["completed"] is True
    cleared = client.patch(f"/api/sets/{second['id']}", json={"rest_seconds": None}).get_json()
    assert cleared["rest_seconds"] is None


def test_set_can_be_marked_as_dropset_or_warmup_but_not_both(client, bench_press):
    # The set row's "..." menu sends both flags in one PATCH so a set is a
    # warmup, a drop set, or neither -- the API just stores what it's given.
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    set_id = client.post(f"/api/workout-exercises/{we['id']}/sets", json={"weight": 100, "reps": 5}).get_json()["id"]

    marked = client.patch(f"/api/sets/{set_id}", json={"is_dropset": True, "is_warmup": False}).get_json()
    assert (marked["is_dropset"], marked["is_warmup"]) == (True, False)

    swapped = client.patch(f"/api/sets/{set_id}", json={"is_warmup": True, "is_dropset": False}).get_json()
    assert (swapped["is_dropset"], swapped["is_warmup"]) == (False, True)

    # A new set copied from a drop set is a regular set, not another drop set.
    client.patch(f"/api/sets/{set_id}", json={"is_dropset": True, "is_warmup": False})
    copy = client.post(f"/api/workout-exercises/{we['id']}/sets", json={}).get_json()
    assert copy["is_dropset"] is False


def test_cannot_delete_exercise_with_history(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    we = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    client.post(f"/api/workout-exercises/{we['id']}/sets", json={"weight": 100, "reps": 5, "completed": True})
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    resp = client.delete(f"/api/exercise-templates/{bench_press.id}")
    assert resp.status_code == 409


def _make_exercise(app, name, muscle_group_id):
    # No `with app.app_context():` here -- the `app` fixture already keeps
    # one open for the whole test (see conftest.py's `bench_press`, which
    # relies on the same thing). Opening a second, nested context here would
    # tear down the scoped session on exit and detach this row before the
    # caller ever reads `.id` from it.
    exercise = ExerciseTemplate(
        name=name,
        muscle_group_id=muscle_group_id,
        equipment="barbell",
        tracking_type="weight_reps",
        is_custom=False,
    )
    db.session.add(exercise)
    db.session.commit()
    return exercise


def test_reorder_workout_exercises(client, app, bench_press, chest_group):
    # Squat sits in the middle and carries a real completed set -- reordering
    # must move it (and its history) intact, unlike the template editor's
    # full-replace approach, which would churn WorkoutExercise ids and
    # cascade-delete any nested WorkoutSet rows if applied here.
    squat = _make_exercise(app, "Squat", chest_group.id)
    deadlift = _make_exercise(app, "Deadlift", chest_group.id)

    workout = client.post("/api/workouts", json={}).get_json()
    we_bench = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id}
    ).get_json()["exercises"][0]
    we_squat = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": squat.id}
    ).get_json()["exercises"][1]
    we_deadlift = client.post(
        f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": deadlift.id}
    ).get_json()["exercises"][2]

    set_resp = client.post(
        f"/api/workout-exercises/{we_squat['id']}/sets",
        json={"weight": 225, "reps": 5, "completed": True},
    ).get_json()

    new_order = [we_deadlift["id"], we_bench["id"], we_squat["id"]]
    resp = client.patch(
        f"/api/workouts/{workout['id']}/exercises/reorder", json={"exercise_ids": new_order}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert [e["id"] for e in body["exercises"]] == new_order
    assert [e["exercise_name"] for e in body["exercises"]] == ["Deadlift", "Bench Press", "Squat"]

    refetched = client.get(f"/api/workouts/{workout['id']}").get_json()
    assert [e["id"] for e in refetched["exercises"]] == new_order

    squat_after = next(e for e in refetched["exercises"] if e["id"] == we_squat["id"])
    assert squat_after["id"] == we_squat["id"]
    assert len(squat_after["sets"]) == 1
    assert squat_after["sets"][0]["id"] == set_resp["id"]
    assert squat_after["sets"][0]["weight"] == 225.0
    assert squat_after["sets"][0]["reps"] == 5


def _start_workout_with_three_exercises(client, bench_press, squat, deadlift):
    workout = client.post("/api/workouts", json={}).get_json()
    ids = []
    for exercise in (bench_press, squat, deadlift):
        we = client.post(
            f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": exercise.id}
        ).get_json()["exercises"][-1]
        ids.append(we["id"])
    return workout, ids


def test_reorder_workout_exercises_rejects_missing_id(client, app, bench_press, chest_group):
    squat = _make_exercise(app, "Squat", chest_group.id)
    deadlift = _make_exercise(app, "Deadlift", chest_group.id)
    workout, ids = _start_workout_with_three_exercises(client, bench_press, squat, deadlift)

    resp = client.patch(
        f"/api/workouts/{workout['id']}/exercises/reorder", json={"exercise_ids": ids[:2]}
    )
    assert resp.status_code == 400

    refetched = client.get(f"/api/workouts/{workout['id']}").get_json()
    assert [e["id"] for e in refetched["exercises"]] == ids


def test_reorder_workout_exercises_rejects_foreign_id(client, app, bench_press, chest_group):
    squat = _make_exercise(app, "Squat", chest_group.id)
    deadlift = _make_exercise(app, "Deadlift", chest_group.id)
    workout_a, ids_a = _start_workout_with_three_exercises(client, bench_press, squat, deadlift)
    client.patch(f"/api/workouts/{workout_a['id']}", json={"finish": True})

    workout_b, ids_b = _start_workout_with_three_exercises(client, bench_press, squat, deadlift)
    bad_order = [ids_a[0], ids_b[1], ids_b[2]]
    resp = client.patch(
        f"/api/workouts/{workout_b['id']}/exercises/reorder", json={"exercise_ids": bad_order}
    )
    assert resp.status_code == 400

    refetched = client.get(f"/api/workouts/{workout_b['id']}").get_json()
    assert [e["id"] for e in refetched["exercises"]] == ids_b


def test_reorder_workout_exercises_rejects_duplicate_id(client, app, bench_press, chest_group):
    squat = _make_exercise(app, "Squat", chest_group.id)
    deadlift = _make_exercise(app, "Deadlift", chest_group.id)
    workout, ids = _start_workout_with_three_exercises(client, bench_press, squat, deadlift)

    resp = client.patch(
        f"/api/workouts/{workout['id']}/exercises/reorder",
        json={"exercise_ids": [ids[0], ids[0], ids[2]]},
    )
    assert resp.status_code == 400

    refetched = client.get(f"/api/workouts/{workout['id']}").get_json()
    assert [e["id"] for e in refetched["exercises"]] == ids


def test_reorder_workout_exercises_rejects_malformed_body(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    client.post(f"/api/workouts/{workout['id']}/exercises", json={"exercise_id": bench_press.id})

    resp = client.patch(
        f"/api/workouts/{workout['id']}/exercises/reorder", json={"exercise_ids": "nope"}
    )
    assert resp.status_code == 400


def _finished_session(client, exercise_id, sets):
    """A completed workout of one exercise with the given (weight, reps) sets, in lb."""
    earlier = client.post("/api/workouts", json={}).get_json()
    we = client.post(f"/api/workouts/{earlier['id']}/exercises", json={"exercise_id": exercise_id}).get_json()
    we_id = we["exercises"][0]["id"]
    for weight, reps in sets:
        set_id = client.post(f"/api/workout-exercises/{we_id}/sets", json={}).get_json()["id"]
        client.patch(f"/api/sets/{set_id}", json={"weight": weight, "weight_unit": "lbs", "reps": reps, "completed": True})
    client.patch(f"/api/workouts/{earlier['id']}", json={"finish": True})


def _template_with(client, exercise_id, **fields):
    body = {"exercise_id": exercise_id, "target_sets": 2, **fields}
    return client.post("/api/templates", json={"name": "T", "exercises": [body]}).get_json()["id"]


def test_double_progression_adds_load_once_the_top_of_the_range_is_reached(client, bench_press):
    _finished_session(client, bench_press.id, [(135, 8), (135, 8)])
    tid = _template_with(client, bench_press.id, target_reps="6-8")
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(140, 6), (140, 6)]


def test_double_progression_repeats_the_load_and_adds_a_rep_below_the_top(client, bench_press):
    _finished_session(client, bench_press.id, [(135, 6), (135, 6)])
    tid = _template_with(client, bench_press.id, target_reps="6-8")
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(135, 7), (135, 7)]


def test_warm_ups_do_not_count_toward_progression(client, bench_press):
    _finished_session(client, bench_press.id, [(95, 8), (135, 6), (135, 6)])
    tid = _template_with(client, bench_press.id, target_reps="6-8")
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(135, 7), (135, 7)]


def test_progression_off_copies_the_last_session(client, bench_press):
    client.patch("/api/settings", json={"progression_method": "off"})
    _finished_session(client, bench_press.id, [(135, 6), (135, 6)])
    tid = _template_with(client, bench_press.id, target_reps="6-8")
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(135, 6), (135, 6)]


def test_linear_progression_adds_load_when_the_target_is_hit(client, bench_press):
    client.patch("/api/settings", json={"progression_method": "linear"})
    _finished_session(client, bench_press.id, [(135, 8), (135, 8)])
    tid = _template_with(client, bench_press.id, target_reps="6-8")
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(140, 8), (140, 8)]


def test_progression_settings_are_validated(client):
    assert client.patch("/api/settings", json={"progression_method": "bogus"}).status_code == 400
    assert client.patch("/api/settings", json={"experience": "pro"}).status_code == 400
    assert client.patch("/api/settings", json={"load_step_lb": 0}).status_code == 400
    body = client.patch("/api/settings", json={"load_step_kg": 2}).get_json()
    assert body["load_step_kg"] == 2.0


def test_default_rep_range_applies_when_the_exercise_has_none(client, bench_press):
    client.patch("/api/settings", json={"default_rep_range": "6-8"})
    _finished_session(client, bench_press.id, [(135, 6), (135, 6)])
    tid = _template_with(client, bench_press.id)
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    # 6 reps is the bottom of 6-8, so the load stays and a rep is added.
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(135, 7), (135, 7)]


def test_exercise_rep_range_overrides_the_default(client, bench_press):
    client.patch("/api/settings", json={"default_rep_range": "6-8"})
    _finished_session(client, bench_press.id, [(135, 8), (135, 8)])
    tid = _template_with(client, bench_press.id, target_reps="8-10")
    sets = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"]
    # 8 is below the top of 8-10, so the load stays and a rep is added.
    assert [(s["planned_weight"], s["planned_reps"]) for s in sets] == [(135, 9), (135, 9)]


def test_default_rep_range_is_validated(client):
    assert client.patch("/api/settings", json={"default_rep_range": "banana"}).status_code == 400
    assert client.patch("/api/settings", json={"default_rep_range": "12-6"}).status_code == 400
    body = client.patch("/api/settings", json={"default_rep_range": " 6 - 8 "}).get_json()
    assert body["default_rep_range"] == "6 - 8"


def test_completing_a_planned_set_makes_its_planned_values_real(client, bench_press):
    _finished_session(client, bench_press.id, [(135, 8), (135, 8)])
    tid = _template_with(client, bench_press.id, target_reps="8-10")
    first = client.post("/api/workouts", json={"template_id": tid}).get_json()["exercises"][0]["sets"][0]
    # Typing a weight keeps the planned reps as ghost text; completing copies the planned reps in.
    client.patch(f"/api/sets/{first['id']}", json={"weight": 140, "weight_unit": "lbs"})
    done = client.patch(f"/api/sets/{first['id']}", json={"completed": True}).get_json()
    assert (done["weight"], done["weight_unit"], done["reps"], done["completed"]) == (140, "lbs", 9, True)
    assert done["planned_weight"] is None and done["planned_reps"] is None
