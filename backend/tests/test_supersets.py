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


def test_three_in_a_row_with_the_same_group_is_a_giant_set(client, bench_press, chest_group):
    """A contiguous run of any size sharing a group is a valid superset -- not just pairs."""
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
    assert [e["superset_group"] for e in exercises] == [1, 1, 1]


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


def test_linking_a_third_exercise_extends_the_chain_into_a_giant_set(client, bench_press, chest_group):
    """Linking we2-we3 when we1-we2 are already linked joins all three into one superset
    (a "giant set") instead of breaking we1 off -- see services/supersets.py link_pair."""
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    _link(client, workout["id"], we1, we2)

    resp = _link(client, workout["id"], we2, we3)
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] is not None
    assert groups[we1] == groups[we2] == groups[we3]


def test_linking_two_existing_chains_merges_them(client, bench_press, chest_group):
    """Linking the last member of one chain to the first member of another merges both into a
    single superset, rather than requiring either side to already be unlinked."""
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    lateral = _second_exercise(chest_group, name="Lateral Raise")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    we4 = _add_exercise(client, workout["id"], lateral.id)
    _link(client, workout["id"], we1, we2)
    _link(client, workout["id"], we3, we4)

    resp = _link(client, workout["id"], we2, we3)
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] == groups[we2] == groups[we3] == groups[we4]
    assert groups[we1] is not None


def test_removing_the_middle_of_a_chain_splits_it(client, bench_press, chest_group):
    """Removing (not deleting) the middle exercise of a 3-exercise giant set from the superset
    splits the chain in two, rather than dissolving the whole thing -- see
    services/supersets.py unlink/normalize_superset_groups."""
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    _link(client, workout["id"], we1, we2)
    _link(client, workout["id"], we2, we3)

    resp = client.patch(f"/api/workouts/{workout['id']}/exercises/{we2}", json={"superset_group": None})
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    # we2 is on its own now; we1 and we3 are no longer *contiguous* (we2 sits between them,
    # ungrouped), so each is down to a single member too, even though they still technically
    # share the old group id -- normalize_superset_groups dissolves both.
    assert groups[we1] is None and groups[we2] is None and groups[we3] is None


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


def test_removing_the_middle_of_a_5_chain_splits_into_two_independent_groups(client, bench_press, chest_group):
    """Removing the middle of a chain of 5 (not 3) leaves two separate runs of 2 each --
    neither dissolves (both are >= 2 long), so without normalize_superset_groups giving the
    second one a fresh id, both would still carry the *same* group number from the original
    5-chain and every group-keyed consumer (equalize_workout_superset_sets, delete_set) would
    wrongly treat all 4 remaining exercises as one superset."""
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    pec_deck = _second_exercise(chest_group, name="Pec Deck")
    cable_fly = _second_exercise(chest_group, name="Cable Crossover")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    we4 = _add_exercise(client, workout["id"], pec_deck.id)
    we5 = _add_exercise(client, workout["id"], cable_fly.id)
    _link(client, workout["id"], we1, we2)
    _link(client, workout["id"], we2, we3)
    _link(client, workout["id"], we3, we4)
    _link(client, workout["id"], we4, we5)

    resp = client.patch(f"/api/workouts/{workout['id']}/exercises/{we3}", json={"superset_group": None})
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we3] is None
    assert groups[we1] is not None and groups[we1] == groups[we2]
    assert groups[we4] is not None and groups[we4] == groups[we5]
    # The two leftover pairs must NOT share a group id, or every group-keyed consumer below
    # would wrongly treat all four as one superset.
    assert groups[we1] != groups[we4]

    # Confirm it's not just the group id that's distinct -- adding a set to we1 must not fan
    # out to we4/we5, which a shared (buggy) group id would cause.
    client.post(f"/api/workout-exercises/{we1}/sets", json={})
    final = client.get(f"/api/workouts/{workout['id']}").get_json()
    counts = {e["id"]: len(e["sets"]) for e in final["exercises"]}
    assert counts[we1] == 1 and counts[we2] == 1
    assert counts[we4] == 0 and counts[we5] == 0


def test_removing_one_end_of_a_chain_leaves_the_rest_linked(client, bench_press, chest_group):
    """Removing the *first* member of a 3-exercise giant set leaves the other two still a
    valid (if now shorter) superset, unlike removing the middle one."""
    incline = _second_exercise(chest_group)
    flye = _second_exercise(chest_group, name="Cable Flye")
    workout = client.post("/api/workouts", json={}).get_json()
    we1 = _add_exercise(client, workout["id"], bench_press.id)
    we2 = _add_exercise(client, workout["id"], incline.id)
    we3 = _add_exercise(client, workout["id"], flye.id)
    _link(client, workout["id"], we1, we2)
    _link(client, workout["id"], we2, we3)

    resp = client.patch(f"/api/workouts/{workout['id']}/exercises/{we1}", json={"superset_group": None})
    groups = {e["id"]: e["superset_group"] for e in resp.get_json()["exercises"]}
    assert groups[we1] is None
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
