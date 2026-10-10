"""Generated workouts: a day built around the muscles that need training.

Frequency is calculated per muscle, once, in services/recency.py. Everything here reads that.

1. A muscle is in need once it's been IN_NEED_DAYS or more since it was worked.
2. The two training groups with the most in-need muscles are the session's focus.
3. Strength exercises are chosen from those two groups, for the in-need muscles inside them.
   The picks alternate between the two groups, so the session splits evenly.

Stretching and cardio are chosen separately and don't use up the strength priorities.
"""

from datetime import date

from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models.exercise_template import ExerciseTemplate
from app.models.workout import Workout, WorkoutExercise, WorkoutSet
from app.services.exercise_templates import GROUP_MUSCLES
from app.services.recency import IN_NEED_DAYS, days_since_trained
from app.services.strength import muscle_shares

NEVER_DAYS = 60  # overdue-ness is capped here, so muscles months out of training don't swamp the rest
STRENGTH_SETS = 3
GROUP_FOCUS = 2  # a session trains this many training groups


def _kind(ex: ExerciseTemplate) -> str | None:
    """Which pool an exercise belongs to. Reps, bodyweight reps and timed holds are all strength
    work. Timed stretches are their own pool, and cardio is separate."""
    if ex.is_stretch:
        return "stretch"
    if ex.tracking_type in ("weight_reps", "bodyweight_reps", "time"):
        return "strength"
    if ex.tracking_type == "cardio":
        return "cardio"
    return None


def _group_name(ex: ExerciseTemplate) -> str | None:
    return ex.app_muscle_group.name if ex.app_muscle_group else None


def _overdue(days: int) -> float:
    return float(min(days, NEVER_DAYS) + 1)


def current_days(days: dict[str, int]) -> dict[str, int]:
    """The muscles that are part of current training: trained within NEVER_DAYS. A muscle untrained
    for longer is left out of the in-need counts, as an old-training muscle isn't what the person is
    training now."""
    return {slug: d for slug, d in days.items() if d <= NEVER_DAYS}


def group_scores(days: dict[str, int]) -> dict[str, tuple[int, int, float]]:
    """Each training group with current muscles: (muscles in need, current muscles, average overdue-ness)."""
    current = current_days(days)
    scores = {}
    for group, members in GROUP_MUSCLES.items():
        trained = [current[m] for m in members if m in current]
        if not trained:
            continue
        in_need = sum(1 for d in trained if d >= IN_NEED_DAYS)
        average = sum(_overdue(d) for d in trained) / len(trained)
        scores[group] = (in_need, len(trained), average)
    return scores


def rank_groups(days: dict[str, int]) -> list[str]:
    """Training groups, by the share of their current muscles that are in need. Ties go to the group
    whose current muscles are most overdue on average."""
    scores = group_scores(days)
    return sorted(scores, key=lambda g: (scores[g][0] / scores[g][1], scores[g][2]), reverse=True)


def group_ranking(today: date) -> list[dict]:
    """For the generate panel: every training group in order of need, with how many of its current
    muscles are in need. The panel selects the top GROUP_FOCUS by default."""
    days = days_since_trained(today)
    scores = group_scores(days)
    return [
        {"name": g, "in_need": scores[g][0], "trained": scores[g][1]}
        for g in rank_groups(days)
    ]


def _priority(ex: ExerciseTemplate, need: dict[str, float]) -> float:
    """How much an exercise helps the muscles that need it: the share-weighted average need of the
    muscles it works that are in `need`. Zero if it works none of them."""
    shares = {slug: share for slug, share in muscle_shares(ex).items() if slug in need}
    total = sum(shares.values())
    if not total:
        return 0.0
    return sum(share * need[slug] for slug, share in shares.items()) / total


def _pick(pool: list[ExerciseTemplate], need: dict[str, float], taken: set[int], require_help: bool):
    """The exercise that helps the most overdue muscles, not already taken. When `require_help`,
    exercises that help none of the muscles in `need` are skipped. Covering a pick lowers the need
    of the muscles it works, so the next pick works something else."""
    best, best_score = None, -1.0
    for ex in pool:
        if ex.id in taken:
            continue
        score = _priority(ex, need)
        if require_help and score <= 0:
            continue
        if score > best_score:
            best, best_score = ex, score
    if best is None:
        return None
    for slug, share in muscle_shares(best).items():
        if slug in need:
            need[slug] = need[slug] * (1 - share)
    return best


def plan(
    count: int,
    stretching: bool,
    cardio: bool,
    today: date,
    familiar_first: bool = True,
    groups: list[str] | None = None,
) -> list[ExerciseTemplate]:
    """The exercises for a generated workout: `count` strength exercises, plus one stretch and one
    cardio if asked for.

    With familiar_first, exercises the person has done before are used first, and unfamiliar ones
    only once those run out. Without it, every exercise is a candidate."""
    exercises = ExerciseTemplate.query.options(selectinload(ExerciseTemplate.app_muscle_group)).all()
    done = {
        we.exercise_id
        for we in WorkoutExercise.query.join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
        .filter(WorkoutSet.completed.is_(True))
        .all()
    }
    everything = {k: [ex for ex in exercises if _kind(ex) == k] for k in ("strength", "stretch", "cardio")}
    familiar = {k: [ex for ex in everything[k] if ex.id in done] for k in everything}
    pool_order = [familiar, everything] if familiar_first else [everything]

    days = days_since_trained(today)  # the one frequency calculation; never-trained muscles are absent
    overdue = {slug: _overdue(d) for slug, d in days.items()}
    in_need = {slug: _overdue(d) for slug, d in current_days(days).items() if d >= IN_NEED_DAYS}
    ranked = rank_groups(days)
    # The person's chosen groups, if they chose any; otherwise the most overdue ones.
    chosen_groups = [g for g in (groups or []) if g in GROUP_MUSCLES] if groups is not None else None
    focus = chosen_groups if chosen_groups is not None else ranked[:GROUP_FOCUS]

    def pick_from_groups(kind: str, groups: set[str] | None, need, taken, require_help: bool):
        for pools in pool_order:
            pool = [ex for ex in pools[kind] if groups is None or _group_name(ex) in groups]
            ex = _pick(pool, need, taken, require_help)
            if ex is not None:
                return ex
        return None

    chosen: list[ExerciseTemplate] = []
    taken: set[int] = set()
    need = dict(in_need)
    for i in range(count):
        ex = None
        # Alternate between the focus groups, so the session splits evenly. When one runs out, the
        # pick goes to the other.
        for k in range(len(focus)):
            ex = pick_from_groups("strength", {focus[(i + k) % len(focus)]}, need, taken, require_help=True)
            if ex is not None:
                break
        if chosen_groups is not None:
            # A chosen session stays within the chosen groups.
            for k in range(len(focus)):
                ex = pick_from_groups("strength", {focus[(i + k) % len(focus)]}, dict(overdue), taken, require_help=False)
                if ex is not None:
                    break
        else:
            # Only when the focus groups have nothing left for the in-need muscles does the plan widen.
            for n in range(len(focus) + 1, len(ranked) + 1):
                if ex is not None:
                    break
                ex = pick_from_groups("strength", set(ranked[:n]), need, taken, require_help=True)
            if ex is None:
                # Nothing in need is left to train, so fall back to the most overdue muscles overall.
                ex = pick_from_groups("strength", None, dict(overdue), taken, require_help=False)
        if ex is None:
            break
        chosen.append(ex)
        taken.add(ex.id)

    for flag, kind in ((stretching, "stretch"), (cardio, "cardio")):
        if flag:
            ex = pick_from_groups(kind, None, dict(overdue), taken, require_help=False)
            if ex is not None:
                chosen.append(ex)
                taken.add(ex.id)
    return chosen


def workout_name(exercises: list[ExerciseTemplate]) -> str:
    """Named after the training groups its strength exercises come from, e.g. "Chest & Legs".
    Stretches and cardio don't count toward the name."""
    groups: list[str] = []
    for ex in exercises:
        group = _group_name(ex)
        if _kind(ex) == "strength" and group and group not in groups:
            groups.append(group)
    if not groups:
        return "Generated workout"
    if len(groups) == 1:
        return groups[0]
    return ", ".join(groups[:-1]) + " & " + groups[-1]


def create_generated_workout(exercises: list[ExerciseTemplate]) -> Workout:
    workout = Workout(name=workout_name(exercises))
    db.session.add(workout)
    db.session.flush()
    for position, ex in enumerate(exercises):
        we = WorkoutExercise(workout_id=workout.id, exercise_id=ex.id, position=position)
        db.session.add(we)
        db.session.flush()
        sets = STRENGTH_SETS if ex.tracking_type in ("weight_reps", "bodyweight_reps") else 1
        for i in range(sets):
            db.session.add(WorkoutSet(workout_exercise_id=we.id, position=i, completed=False))
    db.session.commit()
    return workout
