import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ods_parser import infer_tracking_type, parse_cell, parse_equipment


def test_simple_weighted_sets():
    groups = parse_cell("3×10 @ 105")
    assert len(groups) == 1
    g = groups[0]
    assert g.kind == "sets" and g.sets == 3 and g.reps == 10 and g.weight == 105


def test_multiple_groups_in_one_cell():
    groups = parse_cell("1×10 @ 105, 2×8 @ 105")
    assert [ (g.sets, g.reps, g.weight) for g in groups ] == [(1, 10, 105.0), (2, 8, 105.0)]


def test_bodyweight_sets_no_weight():
    groups = parse_cell("3×10")
    assert groups[0].weight is None and groups[0].reps == 10


def test_time_based_sets():
    groups = parse_cell("2×60s")
    assert groups[0].duration_seconds == 60 and groups[0].reps is None


def test_dropset_suffix():
    groups = parse_cell("1×5 @ 65 drop")
    assert groups[0].is_dropset is True and groups[0].weight == 65


def test_cardio_duration_and_distance():
    groups = parse_cell("15 min, 0.86 mi")
    assert groups[0].kind == "cardio"
    assert groups[0].duration_seconds == 900
    assert groups[0].distance_miles == 0.86


def test_cardio_duration_only():
    groups = parse_cell("5 min")
    assert groups[0].kind == "cardio" and groups[0].duration_seconds == 300


def test_cardio_distance_only():
    groups = parse_cell("1.25 mi")
    assert groups[0].kind == "cardio" and groups[0].distance_miles == 1.25


def test_done_marker():
    groups = parse_cell("done")
    assert groups[0].kind == "done"


def test_equipment_from_suffix():
    assert parse_equipment("Incline Bench (Dumbbell)") == "dumbbell"
    assert parse_equipment("Standing Calf Raise (BW)") == "bodyweight"
    assert parse_equipment("Bench Press") == "other"


def test_infer_tracking_type_weight_reps():
    assert infer_tracking_type("Chest", ["3×10 @ 105", "3×8"]) == "weight_reps"


def test_infer_tracking_type_bodyweight():
    assert infer_tracking_type("Core", ["3×10", "2×8"]) == "bodyweight_reps"


def test_infer_tracking_type_time():
    assert infer_tracking_type("Core", ["2×60s", "3×30s"]) == "time"


def test_infer_tracking_type_cardio_category():
    assert infer_tracking_type("Cardio", ["15 min, 0.86 mi"]) == "cardio"
