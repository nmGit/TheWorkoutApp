Generated workouts
===================

"Generate Workout" builds a workout for you, favoring whichever muscles
have gone longest without training, instead of you remembering what you
last did.

Muscle recency
---------------

Every muscle has a "days since last trained", computed from your completed
workouts: the most recent completed set that worked it, counting only
completed, non-warm-up, non-drop-set sets, and only from exercises that
are strength work (stretches don't count — training a muscle's flexibility
isn't the same as training its strength). A muscle is **in need** once
that's :guilabel:`8` days or more. This is also what colors the muscle map
on the home screen (:doc:`history_and_analytics`) and what the exercise
library's muscle filters sort by.

The "Generate Workout" panel
-----------------------------

Tapping "Generate Workout" (on the home screen) opens a small panel:

- **Strength exercises** — how many to include (1–10). Typing is free; an
  out-of-range or non-numeric value is only corrected once you leave the
  field, not on every keystroke, so you can clear it and retype.
- **Add stretching** / **Add cardio** — one stretch and/or one cardio
  exercise, chosen separately from the strength picks and picked by
  overall overdue-ness rather than the chosen groups below.
- **Prioritize familiar exercises** — when on (the default), exercises
  you've logged a completed set for before are used first; unfamiliar
  exercises (never logged) are only used once the familiar ones run out
  for a given muscle.
- **Groups, most in need first** — a row of chips, one per training group
  (Chest, Back, Shoulders, Arms, Core, Legs), ordered by how overdue they
  are and labeled with *in-need muscles / currently-trained muscles*
  (e.g. "Legs 3/9"). The two most in-need groups are pre-selected; tap a
  chip to add or remove it from the session. At least one group must stay
  selected to generate.

"Generate" builds the workout immediately and takes you to the active
workout screen (:doc:`workout_logging`) — there's no intermediate preview.

How the exercises are picked
------------------------------

1. Days-since-trained is computed once, per muscle, from your history.
2. Each selected group gets a share: how many of its currently-trained
   muscles are in need, divided by how many muscles it has. The chips are
   shown in this order, most-in-need first.
3. Picks alternate between your selected groups, round-robin, so a 4-exercise
   session split across Chest and Legs doesn't end up all Chest. Choosing
   an exercise for a muscle lowers that muscle's remaining need, so the
   next pick for the same group tends to cover a *different* muscle rather
   than stacking the same one.
4. A muscle that hasn't been trained in 60+ days is left out of the
   in-need calculation entirely (but not out of the group's overdue-ness
   ranking) — otherwise one very long-neglected muscle (e.g. an
   adductor stretch nobody does) would dominate its whole group's ranking
   forever.
5. If the chosen groups run out of exercises that help an in-need muscle,
   the pick falls back to whatever's most overdue overall, so the panel
   never under-fills if you picked narrow groups.

None of this is stored as a plan ahead of time — ``POST /api/workouts/generated``
computes the pick and creates the workout in one request: 3 working sets
for each strength exercise (1 for a stretch or cardio pick), all
``completed: false``, with the same :doc:`progressive overload
<progressive_overload>` applied as a template start — the working sets'
next weight/reps are computed from your last session with that exercise
and shown as ghost text, same as :doc:`workout_logging` describes. The one
difference from a template: a generated pick always starts as plain
working sets (no warm-ups or drops, and no per-exercise rep-range
override), since there's no template exercise to carry those settings —
it uses the Settings default rep range for all of them. See
:doc:`../data_flow` for the exact algorithm if you're changing it, and
:doc:`../api/workouts` for the endpoint.
