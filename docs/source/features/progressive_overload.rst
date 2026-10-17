Progressive overload
======================

When you start a workout from a template or generate one, its working
sets can be pre-filled with a little more than last time —
automatically, without you tracking it yourself.

Where it applies
------------------

Progressive overload runs whenever a working set is about to start:
starting a workout from a **template** (``POST /api/workouts
{template_id}``) and :doc:`generating a workout <generated_workouts>`
(``POST /api/workouts/generated``) plan every exercise's working sets
this way up front. It also runs for an exercise's very first set
whenever it's added one at a time — a **blank** workout's exercises, or
any exercise added mid-workout to a workout that's already running
(including a template-started or generated one): the first "+ Add set"
for that exercise computes the same suggestion a template start would,
from the exercise's last session, rather than leaving it bare just
because there's no earlier set *in this session* to copy from yet. Only
an exercise's *second* and later sets fall back to plain "what you did
last time" behavior (copying the first set, see :doc:`workout_logging`)
— by then there's something in this session to copy instead. A generated
workout's exercises always use the Settings default rep range (below)
rather than a per-exercise override, since there's no template exercise
to carry one; the same is true for an exercise added one at a time.

Settings → Generated Workouts
--------------------------------

.. image:: /_static/screenshots/settings_progression.png
   :alt: The Generated Workouts settings page
   :width: 300px
   :align: center

- **Progression** — ``double``, ``linear``, or ``off``:

  - **Double progression** (the default): add reps within the exercise's
    rep range; once every working set reaches the top of the range, add
    load and drop back to the bottom of the range.
  - **Linear progression**: stay at the top-of-range rep target; add load
    whenever every working set reaches it, otherwise repeat the same
    weight and target.
  - **Off**: the next workout's working sets simply copy last session's
    weights and reps, unchanged.

- **Default rep range** (only shown when progression isn't off) — like
  ``8-12``. Used for any exercise that doesn't set its own range (below).
- **Experience** — ``novice`` or ``intermediate``. Stored per the
  schema (see :doc:`../data_model`); not yet read by the progression
  calculation itself.
- **Load step (lb)** / **Load step (kg)** — the amount added when it's
  time to add load, in each unit. Whichever unit your display is
  currently set to is the one used, so switching units changes which step
  applies without needing to re-enter anything.

Per-exercise rep range
-------------------------

Each exercise in a template editor has its own **Rep range** field
(:doc:`templates`). Set, it overrides the Settings default for that
exercise only; left blank, the exercise uses the Settings default. This is
the one place progressive overload can be tuned per exercise — there's no
per-exercise override for progression method or load step.

What counts as a working set
-------------------------------

Only a session's **working sets** feed progression — warm-ups and drop
sets are read, but never written by it:

- A warm-up or drop set's planned value next time is always just a copy
  of that same kind of set from last session, regardless of the
  progression method.
- Progression itself only looks at the completed working sets of the most
  recent *completed* session for that exercise, and only computes a next
  value from them if at least one had a logged weight.
- The "reached the top of the range" check for double/linear progression
  is based on the heaviest working set(s) of that session (within 0.5%
  of the top weight) — lighter back-off sets at the same session don't
  drag the decision down.

How it's shown before you log anything
------------------------------------------

The computed next weight/reps aren't written into the set as a real,
entered value. They're stored separately as that set's *planned* weight,
unit, reps and duration, and shown as placeholder text in the set row —
exactly like the "last time" ghost text used everywhere else, just
computed instead of copied. Completing the set copies whichever fields
you left blank from the planned value into the real one; typing your own
number in a field replaces its ghost text immediately. See
:doc:`workout_logging` and :doc:`../data_model` (``WorkoutSet.planned_*``).

Two small cues call out that a field's ghost text is progression's doing,
not just a copy:

- **Color**: a field's ghost text is muted green when progression raised
  it over what that same set was last time (reps 8 → 12, say), muted
  amber when it lowered it (reps 12 → 8, when the weight went up
  instead), and the ordinary muted grey otherwise — including a plain
  copy (warm-ups, drops, progression off), since nothing changed there to
  color. The comparison is per field: in a double-progression jump from
  3×8 @ 120 to 3×12 @ 120, only the "12" turns green; the next session's
  jump to 3×8 @ 140 turns "140" green and "8" amber, since the rep count
  dropped back to the bottom of the range.
- **A small "P"** appears under the set number (alongside the warm-up
  "W"/drop "D" badges — a set is never both), in one of two colors:
  green when progression actually raised a value over what that same set
  was last time, grey when progression ran (there's history to compare
  against, and it isn't off in Settings) but the computed target happens
  to match what was already done — double progression in particular can
  do this when it's catching a weaker set up to the session's best one
  rather than asking for more than was already shown (3×8, 3×8, 3×7 last
  time plans 3×8 next, which is only new for that third set). No badge at
  all means a plain copy — no progression to speak of for this set
  (warm-ups, drops, progression off, or no history yet). It disappears
  once the set is completed, the same moment its planned values are
  cleared, since by then it's no longer a suggestion.
