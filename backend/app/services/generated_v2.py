"""Generated strength data: the live method (see docs/source/features/strength_score.rst).

Entered data (sets, exercises, muscle lists) goes in; generated data comes out. Nothing
here is stored, so all of it can be regenerated from the entered data.

How it works, in short:
- Each exercise is compared only with its own sessions from the last WINDOW_DAYS.
- A session's value for an exercise is the mean of its best TOP_SETS counting sets.
- A session is set aside as a likely entry error if it is more than OUTLIER_RATIO away
  from its baseline. Set-aside sessions don't feed later baselines.
- Each muscle's change is the average of its exercises' changes, weighted by each
  exercise's share for that muscle times its counting sets. The average is pulled
  towards zero by SHRINKAGE, so thin evidence gives a small change.
- Each muscle reports its evidence: the total weight behind its change.
"""

import math
from collections import defaultdict
from dataclasses import dataclass

from app.models.workout import Workout
from app.services.strength import (
    HOLD,
    HOLD_EXCLUDED_GROUPS,
    LOAD,
    MIN_HISTORY,
    _estimated_one_rm_kg,
    _is_hold_set,
    _planned_muscles,
    history_before,
    muscle_shares,
)
from app.services.units import convert_weight

TOP_SETS = 3
MAX_REPS = 15
FULL_WEIGHT_REPS = 8
WINDOW_DAYS = 90
HALF_LIFE_DAYS = 21
OUTLIER_RATIO = 1.6
SHRINKAGE = 1.0  # acts like one set of "no change"
REFERENCE_WINDOW = 6  # earlier sessions used to estimate an exercise's reference e1RM


def rep_weight(reps: int) -> float:
    """Full weight up to 8 reps, falling linearly to 0.5 at 15."""
    if reps <= FULL_WEIGHT_REPS:
        return 1.0
    return max(0.5, 1 - 0.5 * (reps - FULL_WEIGHT_REPS) / (MAX_REPS - FULL_WEIGHT_REPS))


def _is_load_set(s) -> bool:
    return (
        s.completed
        and not s.is_warmup
        and not s.is_dropset
        and s.weight is not None
        and float(s.weight) > 0
        and s.reps is not None
        and 1 <= s.reps <= MAX_REPS
        and s.weight_unit in ("lbs", "kg")
    )


def generated_rir(reps: int, weight_kg: float, reference_e1rm: float) -> float:
    """Reps in reserve estimated from the load's share of the reference e1RM, using the
    Epley inverse: the reps this load would allow to failure is 30 * (E / w - 1)."""
    reps_to_failure = 30.0 * (reference_e1rm / weight_kg - 1.0)
    return min(5.0, max(0.0, reps_to_failure - reps))


@dataclass
class ExerciseSession:
    exercise_id: int
    kind: str
    value: float
    muscle_weights: dict[str, float]  # each muscle's share of this exercise
    counting_sets: int
    best_e1rm: float | None  # for building the next session's reference
    hard_sets: int           # generated: counting sets with an estimated RIR of 3 or less


def _exercise_sessions(workout: Workout, references: dict[int, float]) -> list[ExerciseSession]:
    out = []
    for we in workout.exercises:
        ex = we.exercise
        if ex is None:
            continue
        shares = muscle_shares(ex)
        if ex.tracking_type == "weight_reps":
            ref = references.get(ex.id)
            scored = []
            hard = 0
            for s in we.sets:
                if not _is_load_set(s):
                    continue
                w = convert_weight(float(s.weight), s.weight_unit, "kg")
                e = _estimated_one_rm_kg(w, s.reps)
                scored.append((e, rep_weight(s.reps)))
                if ref is not None and generated_rir(s.reps, w, ref) <= 3:
                    hard += 1
            if not scored:
                continue
            top = sorted(scored, key=lambda c: c[0], reverse=True)[:TOP_SETS]
            value = sum(e * rw for e, rw in top) / sum(rw for _, rw in top)
            out.append(ExerciseSession(ex.id, LOAD, value, shares, len(scored), max(e for e, _ in scored), hard))
        elif ex.tracking_type == "time":
            group = ex.app_muscle_group.name if ex.app_muscle_group else None
            if group in HOLD_EXCLUDED_GROUPS:
                continue
            holds = sorted((float(s.duration_seconds) for s in we.sets if _is_hold_set(s)), reverse=True)[:TOP_SETS]
            if not holds:
                continue
            out.append(ExerciseSession(ex.id, HOLD, sum(holds) / len(holds), shares, len(holds), None, 0))
    return out


class V2Series:
    """Replays completed workouts oldest first, producing generated data per workout."""

    def __init__(self):
        # (exercise id, kind) -> [(session start, natural log of the session value)]
        self.history: dict[tuple[int, str], list[tuple]] = defaultdict(list)
        self.best_history: dict[int, list[float]] = defaultdict(list)

    def reference(self, exercise_id: int) -> float | None:
        recent = self.best_history.get(exercise_id)
        if not recent:
            return None
        return max(recent[-REFERENCE_WINDOW:])

    def _baseline(self, key, when):
        """Log baseline from the sessions in the window, or None if there are too few."""
        recent = []
        for started, log_value in self.history.get(key, []):
            days = (when - started).total_seconds() / 86400
            if 0 < days <= WINDOW_DAYS:
                recent.append((days, log_value))
        if len(recent) < MIN_HISTORY:
            return None
        weights = [0.5 ** (days / HALF_LIFE_DAYS) for days, _ in recent]
        return sum(w * v for w, (_, v) in zip(weights, recent)) / sum(weights)

    def step(self, workout: Workout) -> dict:
        when = workout.started_at
        refs = {ex_id: self.reference(ex_id) for ex_id in self.best_history}
        sessions = _exercise_sessions(workout, {k: v for k, v in refs.items() if v is not None})

        # muscle -> [(log change, evidence weight)]
        terms = defaultdict(list)
        set_aside = set()  # sessions judged to be entry errors
        for sess in sessions:
            key = (sess.exercise_id, sess.kind)
            base = self._baseline(key, when)
            if base is None:
                # Too little history to compare with. Still refuse a session that is far
                # above the exercise's best so far, so an entry error can't become history.
                ref = refs.get(sess.exercise_id)
                if ref is not None and sess.value > OUTLIER_RATIO * ref:
                    set_aside.add(id(sess))
                continue
            change = math.log(sess.value) - base
            if abs(change) > math.log(OUTLIER_RATIO):
                set_aside.add(id(sess))
                continue
            for slug, share in sess.muscle_weights.items():
                terms[slug].append((change, share * sess.counting_sets))

        # Fold this workout into the history, after scoring it. Set-aside sessions are skipped.
        for sess in sessions:
            key = (sess.exercise_id, sess.kind)
            if id(sess) not in set_aside:
                self.history[key].append((when, math.log(sess.value)))
                if sess.best_e1rm is not None:
                    self.best_history[sess.exercise_id].append(sess.best_e1rm)

        worked = {slug for sess in sessions for slug in sess.muscle_weights}
        muscles = {}
        for slug, pairs in terms.items():
            evidence = sum(e for _, e in pairs)
            change = sum(c * e for c, e in pairs) / (evidence + SHRINKAGE)
            muscles[slug] = {"status": "scored", "ratio": math.exp(change), "evidence": round(evidence, 2)}
        for slug in worked - set(muscles):
            muscles[slug] = {"status": "no_baseline", "ratio": None, "evidence": 0.0}
        for slug in _planned_muscles(workout) - worked:
            muscles[slug] = {"status": "pending", "ratio": None, "evidence": 0.0}

        scored = [m["ratio"] for m in muscles.values() if m["status"] == "scored"]
        score = None
        if scored:
            score = math.exp(sum(math.log(r) for r in scored) / len(scored))
        return {
            "workout_id": workout.id,
            "started_at": workout.started_at,
            "template_id": workout.template_id,
            "score": score,
            "muscles": muscles,
        }


def score_series_v2(workouts: list[Workout]) -> list[dict]:
    """Generated strength data for each of `workouts` (oldest first), in one pass."""
    series = V2Series()
    return [series.step(w) for w in workouts]


def strength_for_workout(workout: Workout) -> dict:
    """The generated strength data for one workout, from the completed workouts before it.
    Works for a workout still in progress, which is never part of its own history."""
    point = score_series_v2(history_before(workout) + [workout])[-1]
    return {"score": point["score"], "muscles": point["muscles"]}
