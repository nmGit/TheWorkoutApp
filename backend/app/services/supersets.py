"""Supersets: two exercises done back to back as one round, within a template or a workout.

A superset is always exactly a *pair* -- two adjacent (by position) exercises sharing the same
non-null ``superset_group`` value, not a globally unique id, just one scoped to that template's or
workout's own exercises. There's no separate table: membership lives entirely on
``TemplateExercise.superset_group`` / ``WorkoutExercise.superset_group``. (Longer "giant sets" of
3+ aren't supported -- keeping a pair's membership well-defined under reordering, merging and
splitting is already most of this module; a third member would need deciding which existing pair
it joins, which isn't an obviously right call to make automatically.)

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
    """Clear `superset_group` on anything that isn't part of a valid pair: a contiguous run (in
    `items`' own order) of exactly two members sharing the same group. A run of one (its old
    partner moved away, or was removed) is dissolved; a run of three or more (shouldn't normally
    happen, since supersets are only ever formed as pairs, but could follow unusual direct API
    use) keeps the first two and frees the rest, rather than guessing which one(s) meant it.
    `items` must already be in position order."""
    i, n = 0, len(items)
    while i < n:
        group = items[i].superset_group
        if group is None:
            i += 1
            continue
        j = i
        while j + 1 < n and items[j + 1].superset_group == group:
            j += 1
        run = items[i : j + 1]
        if len(run) < 2:
            run[0].superset_group = None
        elif len(run) > 2:
            for extra in run[2:]:
                extra.superset_group = None
        i = j + 1


def link_pair(items, first_id, second_id) -> None:
    """Pairs the two given items (by `.id`) into a superset, breaking either one's existing
    pairing first -- a superset here is always exactly two exercises, so forming a new pair always
    frees whoever the two were previously paired with. Allocates a fresh `superset_group` value,
    unused among `items`. Does not check adjacency; callers (routes) that require it validate that
    themselves so they can give a clearer error."""
    first = next(item for item in items if item.id == first_id)
    second = next(item for item in items if item.id == second_id)
    old_groups = {first.superset_group, second.superset_group} - {None}
    for item in items:
        if item.superset_group in old_groups and item.id not in (first_id, second_id):
            item.superset_group = None
    group = max((item.superset_group or 0 for item in items), default=0) + 1
    first.superset_group = second.superset_group = group


def unlink(items, item_id) -> None:
    """Breaks whatever pairing the given item (by `.id`) is in, if any -- clearing both sides,
    since a superset here is always exactly two exercises."""
    item = next(x for x in items if x.id == item_id)
    old_group = item.superset_group
    item.superset_group = None
    if old_group is not None:
        for sibling in items:
            if sibling.id != item_id and sibling.superset_group == old_group:
                sibling.superset_group = None


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
