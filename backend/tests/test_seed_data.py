import json
import os

SEED_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "seed_data", "exercises.json"
)


def _load():
    with open(SEED_FILE) as f:
        return json.load(f)


def test_bodyweight_movements_are_not_weight_reps():
    # A handful of historical weighted-vest sessions on these bodyweight
    # movements would otherwise flip the mechanical column-level inference
    # to weight_reps (see docs/data_migration.rst) -- these are corrected
    # by hand in the seed file and should stay corrected.
    data = _load()
    by_name = {e["name"]: e for e in data["exercises"]}
    for name in ("Push Up", "Chest Dip", "Tricep Dip"):
        assert by_name[name]["tracking_type"] == "bodyweight_reps", name
