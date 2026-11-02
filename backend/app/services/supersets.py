"""Supersets: two or more exercises done back to back as one round ("giant sets" when there are
more than two), within a template or a workout.

A superset is a contiguous (by position) run of two or more exercises sharing the same non-null
``superset_group`` value, not a globally unique id, just one scoped to that template's or
workout's own exercises. There's no separate table: membership lives entirely on
``TemplateExercise.superset_group`` / ``WorkoutExercise.superset_group``.

A superset's members are always forced to the same set count -- ``target_sets`` for a template
(the working-set count the workout starts with; see services/sets_plan.py), or the actual number
of logged ``WorkoutSet`` rows for a live/completed workout. Both directions are enforced here:
linking, reordering or removing an exercise can only ever require adding sets to catch a member
up (never removes any -- that stays an explicit, single-exercise action, see routes/workouts.py
``delete_set``), so the functions below only grow set counts, never shrink them.
"""

from app.extensions import db
from app.models.workout import WorkoutSet


def normalize_superset_groups(items) -> None:
    """Clear `superset_group` on anything that isn't part of a valid superset: a contiguous run
    (in `items`' own order) of two or more members sharing the same group. A run of one (its
    only neighbor moved away, was removed, or was itself just unlinked) is dissolved -- a lone
    exercise is never "a superset" by itself; a run of any larger size is left alone, a "giant
    set". `items` must already be in position order."""
    i, n = 0, len(items)
    while i < n:
        group = items[i].superset_group
        if group is None:
            i += 1
            continue
        j = i
        while j + 1 < n and items[j + 1].superset_group == group:
            j += 1
        if j == i:  # a run of exactly one
            items[i].superset_group = None
        i = j + 1


def link_pair(items, first_id, second_id) -> None:
    """Links the two given adjacent items (by `.id`) into one superset, joining whichever
    superset(s) either one already belongs to rather than always starting a fresh one --
    repeating this across a run of adjacent exercises builds one growing "giant set" instead of
    a series of disconnected pairs, and linking two exercises that each already head their own
    chain merges the two into one. Allocates a fresh `superset_group` value, unused among
    `items`, only when neither side is already in one. Does not check adjacency; callers
    (routes) that require it validate that themselves so they can give a clearer error."""
    first = next(item for item in items if item.id == first_id)
    second = next(item for item in items if item.id == second_id)
    group = first.superset_group
    if group is None:
        group = second.superset_group
    if group is None:
        group = max((item.superset_group or 0 for item in items), default=0) + 1
    # Whichever side had a *different* existing group -- joining two established chains into
    # one, or an exercise moving straight from one superset into another -- adopts this one.
    old_groups = {first.superset_group, second.superset_group} - {None, group}
    for item in items:
        if item.superset_group in old_groups:
            item.superset_group = group
    first.superset_group = second.superset_group = group


def unlink(items, item_id) -> None:
    """Removes the given item (by `.id`) from whatever superset it's in, if any, without
    touching any other member. If that item was in the middle of a chain, the pieces on
    either side keep their membership (and their shared group id) for now; callers call
    `normalize_superset_groups` afterward, which dissolves either piece if removing this item
    left it down to a single member."""
    item = next(x for x in items if x.id == item_id)
    item.superset_group = None


def sync_template_superset_sets(items) -> None:
    """Within each valid (contiguous) superset, force every member's `target_sets` to whatever
    the first (topmost) member's is. Call after `normalize_superset_groups` so a just-dissolved
    group's lone leftover member is left alone."""
    first_seen: dict[int, int | None] = {}
    for item in items:
        group = item.superset_group
        if group is None:
            continue
        if group not in first_seen:
            first_seen[group] = item.target_sets
        else:
            item.target_sets = first_seen[group]


def equalize_workout_superset_sets(workout) -> None:
    """Within each valid superset in this workout, pad every member's sets up to the longest
    member's count by appending empty (uncompleted) sets at the end -- never removes any. Also
    normalizes grouping first, since this runs after anything that could have changed position or
    membership (reordering, linking/unlinking, removing an exercise)."""
    exercises = sorted(workout.exercises, key=lambda we: we.position)
    normalize_superset_groups(exercises)

    groups: dict[int, list] = {}
    for we in exercises:
        if we.superset_group is not None:
            groups.setdefault(we.superset_group, []).append(we)

    for members in groups.values():
        counts = {we.id: len(we.sets) for we in members}
        target = max(counts.values())
        for we in members:
            for position in range(counts[we.id], target):
                db.session.add(WorkoutSet(workout_exercise_id=we.id, position=position, completed=False))
