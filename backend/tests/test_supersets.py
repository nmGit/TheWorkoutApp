"""Supersets: two exercises linked to be done back to back, forced to the same set count.
See app/services/supersets.py."""

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate


def _second_exercise(chest_group, name="Incline Press"):
    ex = ExerciseTemplate(
        name=name,
        muscle_group_id=chest_group.id,
        equipment="barbell",
        tracking_type="weight_reps",
        is_custom=False,
    )
    db.session.add(ex)
    db.session.commit()
    return ex


def _add_exercise(client, workout_id, exercise_id):
    """Adds an exercise to a workout and returns its new WorkoutExercise id."""
    body = client.post(f"/api/workouts/{workout_id}/exercises", json={"exercise_id": exercise_id}).get_json()
    return body["exercises"][-1]["id"]


def _link(client, workout_id, first_id, second_id):
    return client.post(f"/api/workouts/{workout_id}/exercises/link", json={"first_id": first_id, "second_id": second_id})


# ----------------------------------------------------------------- templates


def test_superset_forces_equal_target_sets(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)

    resp = client.post(
        "/api/templates",
        json={
            "name": "Push",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 4, "superset_group": 1},
                {"exercise_id": incline.id, "target_sets": 2, "superset_group": 1},
            ],
        },
    )
    exercises = resp.get_json()["exercises"]
    # The second member's target_sets is forced to match the first's.
    assert [e["target_sets"] for e in exercises] == [4, 4]
    assert [e["superset_group"] for e in exercises] == [1, 1]


def test_non_contiguous_superset_group_is_dissolved(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")

    resp = client.post(
        "/api/templates",
        json={
            "name": "Push",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 3, "superset_group": 1},
                {"exercise_id": flye.id, "target_sets": 3},  # not grouped, sits between them
                {"exercise_id": incline.id, "target_sets": 3, "superset_group": 1},
            ],
        },
    )
    exercises = resp.get_json()["exercises"]
    # The two "1"s aren't adjacent, so the group never forms -- not silently merged with the
    # exercise that actually ended up next to each of them.
    assert [e["superset_group"] for e in exercises] == [None, None, None]


def test_three_in_a_row_with_the_same_group_keeps_only_the_first_pair(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")

    resp = client.post(
        "/api/templates",
        json={
            "name": "Push",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 3, "superset_group": 1},
                {"exercise_id": incline.id, "target_sets": 3, "superset_group": 1},
                {"exercise_id": flye.id, "target_sets": 3, "superset_group": 1},
            ],
        },
    )
    exercises = resp.get_json()["exercises"]
    assert [e["superset_group"] for e in exercises] == [1, 1, None]


def test_updating_a_template_exercise_in_a_superset_resyncs_its_siblings(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    tid = client.post(
        "/api/templates",
        json={
            "name": "Push",
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 3, "superset_group": 1},
                {"exercise_id": incline.id, "target_sets": 3, "superset_group": 1},
            ],
        },
    ).get_json()["id"]

    # Editing just one member's target_sets (the editor sends the whole array back) still
    # re-syncs both to the same value -- the server enforces it, not just the UI.
    resp = client.patch(
        f"/api/templates/{tid}",
        json={
            "exercises": [
                {"exercise_id": bench_press.id, "target_sets": 5, "superset_group": 1},
                {"exercise_id": incline.id, "target_sets": 2, "superset_group": 1},
            ]
        },
    )
    exercises = resp.get_json()["exercises"]
    assert [e["target_sets"] for e in exercises] == [5, 5]


def test_save_as_template_preserves_superset_grouping(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)

    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    _link(client, workout["id"], we1, we2)
    for we_id in (we1, we2):
        set_id = client.post(f"/api/workout-exercises/{we_id}/sets", json={}).get_json()["id"]
        client.patch(f"/api/sets/{set_id}", json={"weight": 100, "reps": 8, "completed": True})
    client.patch(f"/api/workouts/{workout['id']}", json={"finish": True})

    template = client.post(f"/api/templates/from-workout/{workout['id']}").get_json()
    groups = [e["superset_group"] for e in template["exercises"]]
    assert groups[0] is not None and groups[0] == groups[1]


# ------------------------------------------------------------------ workouts


def test_linking_requires_adjacent_exercises(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)

    assert _link(client, workout["id"], we1, we3).status_code == 400


def test_linking_workout_exercises_equalizes_set_counts(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)

    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    for _ in range(3):
        client.post(f"/api/workout-exercises/{we1}/sets", json={})
    client.post(f"/api/workout-exercises/{we2}/sets", json={})

    resp = _link(client, workout["id"], we1, we2)
    assert resp.status_code == 200
    counts = {e["id"]: len(e["sets"]) for e in resp.get_json()["exercises"]}
    assert counts[we1] == 3 and counts[we2] == 3  # we2 was padded up to we1's count
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] is not None and groups[we1] == groups[we2]


def test_linking_a_new_pair_breaks_the_old_one(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    _link(client, workout["id"], we1, we2)

    resp = _link(client, workout["id"], we2, we3)
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] is None  # its old partner moved on
    assert groups[we2] is not None and groups[we2] == groups[we3]


def test_unlinking_clears_both_sides(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    _link(client, workout["id"], we1, we2)

    resp = client.patch(f"/api/workouts/{workout['id']}/exercises/{we1}", json={"superset_group": None})
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] is None and groups[we2] is None


def test_setting_a_specific_group_via_patch_is_rejected(client, bench_press):
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    resp = client.patch(f"/api/workouts/{workout['id']}/exercises/{we1}", json={"superset_group": 9})
    assert resp.status_code == 400


def test_adding_a_set_fans_out_to_superset_siblings(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)

    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    _link(client, workout["id"], we1, we2)

    client.post(f"/api/workout-exercises/{we1}/sets", json={})
    final = client.get(f"/api/workouts/{workout['id']}").get_json()
    counts = {e["id"]: len(e["sets"]) for e in final["exercises"]}
    assert counts[we1] == 1 and counts[we2] == 1


def test_deleting_a_set_fans_out_to_superset_siblings(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)

    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    _link(client, workout["id"], we1, we2)
    client.post(f"/api/workout-exercises/{we1}/sets", json={})  # -> both at 1 set (equalized)

    we_list = client.get(f"/api/workouts/{workout['id']}").get_json()["exercises"]
    we1_set_id = next(e for e in we_list if e["id"] == we1)["sets"][-1]["id"]
    client.delete(f"/api/sets/{we1_set_id}")

    final = client.get(f"/api/workouts/{workout['id']}").get_json()
    counts = {e["id"]: len(e["sets"]) for e in final["exercises"]}
    assert counts[we1] == 0 and counts[we2] == 0


def test_reordering_apart_dissolves_the_superset(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")

    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    _link(client, workout["id"], we1, we2)

    # Drag the third exercise between the two superset members.
    resp = client.patch(
        f"/api/workouts/{workout['id']}/exercises/reorder", json={"exercise_ids": [we1, we3, we2]}
    )
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] is None and groups[we2] is None


def test_removing_the_middle_of_a_superset_is_fine(client, bench_press, chest_group):
    """Removing an unrelated exercise that happened to sit between two other exercises never
    joins them into something they weren't -- there's nothing to normalize here since neither
    was ever grouped. Mostly a smoke test that remove doesn't choke on the new normalize call."""
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    _link(client, workout["id"], we2, we3)

    assert client.delete(f"/api/workouts/{workout['id']}/exercises/{we1}").status_code == 204
    final = client.get(f"/api/workouts/{workout['id']}").get_json()
    groups = {e["id"]: e["superset_group"] for e in final["exercises"]}
    assert groups[we2] is not None and groups[we2] == groups[we3]


def test_workout_exercise_serializes_superset_group(client, bench_press, chest_group):
    incline = _second_exercise(chest_group)
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    body = client.get(f"/api/workouts/{workout['id']}").get_json()
    assert all(e["superset_group"] is None for e in body["exercises"])

    _link(client, workout["id"], we1, we2)
    body = client.get(f"/api/workouts/{workout['id']}").get_json()
    groups = {e["id"]: e["superset_group"] for e in body["exercises"]}
    assert groups[we1] is not None and groups[we1] == groups[we2]
