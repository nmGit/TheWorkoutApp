"""Compare the live generated strength data with the v2 candidate on a database.

Usage (point it at a COPY of the database, it only reads):
    DATABASE_URL=sqlite:////path/to/copy.db .venv/bin/python scripts/evaluate_generated.py

Reports, for both methods:
- coverage: how many workouts get a score, and how many muscles each one scores;
- swing: how much a muscle's ratio moves between consecutive workouts, split by whether
  the exercises changed. Good generated data moves less when only the exercises change;
- prediction (v2 only): one-step-ahead error of each exercise's next session value
  under different baseline settings. This is the ground truth that exists without RPE.
"""

import math
import os
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app  # noqa: E402
from app.services.generated_v2 import _exercise_sessions, score_series_v2  # noqa: E402
from app.services.strength import MIN_HISTORY, _muscle_weights, completed_workouts, score_series  # noqa: E402


def _exercise_set(workout):
    return frozenset(we.exercise_id for we in workout.exercises if we.exercise is not None)


def _muscle_exercises(workout):
    """muscle slug -> frozenset of exercise ids that work it in this workout."""
    out = defaultdict(set)
    for we in workout.exercises:
        if we.exercise is None:
            continue
        for slug in _muscle_weights(we.exercise):
            out[slug].add(we.exercise_id)
    return {m: frozenset(ids) for m, ids in out.items()}


def swing_stats(workouts, series, label):
    """For each muscle scored in consecutive workouts, how far its ratio moved. Split by
    whether the exercises that work that muscle were the same in both workouts."""
    same, changed = [], []
    prev_ratio, prev_ex = None, None
    for workout, point in zip(workouts, series):
        ratios = {m: math.log(v["ratio"]) for m, v in point["muscles"].items() if v["status"] == "scored"}
        ex = _muscle_exercises(workout)
        if prev_ratio is not None:
            for m in set(prev_ratio) & set(ratios):
                moved = abs(ratios[m] - prev_ratio[m])
                (same if prev_ex.get(m) == ex.get(m) else changed).append(moved)
        prev_ratio, prev_ex = ratios, ex
    print(label)
    print(f"  muscle moved (|change in log ratio|), its exercises unchanged: {statistics.mean(same):.3f} (n={len(same)})")
    print(f"  muscle moved (|change in log ratio|), its exercises changed:   {statistics.mean(changed):.3f} (n={len(changed)})")


def large_moves(workouts, series, label):
    """Single-session moves of more than 2x in either direction, per muscle. These are the
    jumps that show up as colour flips on the body map."""
    count, total = 0, 0
    prev = {}
    for workout, point in zip(workouts, series):
        cur = {m: v["ratio"] for m, v in point["muscles"].items() if v["status"] == "scored"}
        for m in set(prev) & set(cur):
            total += 1
            if abs(math.log(cur[m] / prev[m])) > math.log(2):
                count += 1
        prev = cur
    print(f"{label}: single-session moves over 2x: {count} of {total} ({100 * count / max(total, 1):.1f}%)")


def coverage(series, label):
    scored = [p for p in series if p["score"] is not None]
    per = [len([m for m in p["muscles"].values() if m["status"] == "scored"]) for p in series]
    print(f"{label}: workouts with a score {len(scored)}/{len(series)}, "
          f"muscles scored per workout (mean) {statistics.mean(per):.2f}")


def exercise_prediction(workouts):
    """Per exercise and kind: predict each session's value from earlier sessions only."""
    per_exercise = {}
    for workout in workouts:
        for sess in _exercise_sessions(workout, {}):
            per_exercise.setdefault((sess.exercise_id, sess.kind), []).append(sess.value)

    def run(predict):
        errors = []
        for values in per_exercise.values():
            for k in range(MIN_HISTORY, len(values)):
                pred = predict(values[:k])
                errors.append(abs(math.log(values[k] / pred)))
        return statistics.mean(errors), statistics.pstdev(errors), len(errors)

    def ema(span):
        alpha = 2 / (span + 1)

        def predict(history):
            b = history[0]
            for v in history[1:]:
                b = alpha * v + (1 - alpha) * b
            return b

        return predict

    def median6(history):
        return statistics.median(history[-6:])

    print("exercise prediction, mean |log error| of the next session (lower is better):")
    results = {}
    for name, predict in [(f"EMA span {s}", ema(s)) for s in (3, 5, 8, 12, 20)] + [("median of last 6", median6)]:
        mean, sd, n = run(predict)
        results[name] = (mean, sd, n)
        print(f"  {name:18s} mean error {mean:.4f}  (sd {sd:.4f}, n={n})")
    return results


def main():
    app = create_app()
    with app.app_context():
        workouts = completed_workouts()
        print(f"{len(workouts)} completed workouts")
        live = score_series(workouts)
        v2 = score_series_v2(workouts)
        coverage(live, "live")
        coverage(v2, "v2  ")
        swing_stats(workouts, live, "live")
        swing_stats(workouts, v2, "v2")
        large_moves(workouts, live, "live")
        large_moves(workouts, v2, "v2")
        exercise_prediction(workouts)


if __name__ == "__main__":
    main()
