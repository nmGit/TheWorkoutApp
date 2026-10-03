Rest timers
============

The rest timer is what makes logging *during* a workout viable instead of
reconstructing it from memory afterward — it needs to survive
interruptions (locking the phone, switching apps, an accidental refresh)
without the lifter having to think about it.

Behavior
--------

- **Auto-starts** the moment a set is marked ``completed`` (see
  :doc:`workout_logging`). Duration = that set's own ``rest_seconds`` if it
  has one, otherwise its *ghost* value (see :ref:`features/rest_timers:The
  rest field and its ghost text` below). Completing the set also saves that
  value into the set, so the rest box fills in.
- **Editing the rest field of the set whose timer is running re-targets the
  timer**, keeping the time already elapsed: with a 2:00 timer 20 seconds in,
  changing the field to 1:30 leaves 1:10 on the clock (the 20 elapsed seconds
  are not reset or forgotten; if the new total is already shorter than what has
  elapsed, the rest is simply over). Clearing the field falls back to the ghost
  value. The change is applied when you leave the field, not on every keystroke.
  Editing a *different* set's field never touches a running timer.
- Rendered as a persistent bar/sheet anchored to the bottom of the active
  workout screen: countdown (``m:ss``), a progress ring/bar, ``-15s`` /
  ``+15s`` adjustment buttons, and a skip button.
- Starting a new set's timer while one is already running **replaces** it
  (does not stack) — only one rest timer is meaningful at a time.
- On expiry: a notification sound plus (where the browser grants
  permission) a system notification, so the lifter doesn't have to keep
  the tab in view. The bar stays visible in an "elapsed since rest ended"
  state (counting up in a muted color) rather than disappearing, since
  going a little over is normal and useful to see at a glance.
- **Survives reloads**: the running timer's start time, end time, total
  duration and the set it belongs to are persisted to ``localStorage`` (keyed
  by the active workout id) the moment it starts. On load, the app computes
  remaining time from the stored timestamps rather than resuming a stored
  countdown — this makes it correct even if the tab was fully closed and
  reopened after the timer would have finished.
- Finishing or discarding the workout clears any running timer.

The rest field and its ghost text
------------------------------------

Every set row has a rest field, shown and typed as ``m:ss`` (``1:30``,
``0:45``); a bare number is read as seconds (``90`` becomes ``1:30``), and
anything unparseable snaps back to what was there. The same format is used for
the global default in Settings.

While a set has no rest of its own, the field shows a greyed-out **ghost**
value, chosen the same way a weight's ghost is (what you did last time), in
this order:

1. the rest of the nearest *earlier* set in this exercise block that has one —
   so changing one set's rest changes the suggestion for every set after it
   (they don't get a copy of the value written to them; their ghost just
   follows, and a set you've filled in yourself keeps its own);
2. the rest used for this same set position the last time this exercise was
   logged;
3. the last rest used the last time this exercise was logged;
4. the global default from Settings (:doc:`bodyweight_and_settings`, 90 seconds
   out of the box).

Configuration
--------------

- ``rest_seconds`` is stored per set (``WorkoutSet.rest_seconds``, see
  :doc:`../data_model`), not as an exercise-level config value — logged
  data, like ``weight``, rather than a setting to tune ahead of time. It is
  filled in when you type a value or complete the set, and is deliberately
  **not** copied onto a new set by "+ Add set" (unlike weight), because an
  empty field has to stay a ghost for later sets to follow earlier edits. This
  replaced an earlier per-exercise ``default_rest_seconds`` config field that,
  in practice, was never used: real usage always fell through to the global
  default anyway (see :ref:`data_migration:Merging Exercise into
  ExerciseTemplate`).
- The ``-15s``/``+15s`` buttons on the running timer are a one-off nudge for
  that rest only: they change the running timer (and its progress ring) but do
  not change the set's stored value or later sets' ghost text.

Non-goals
---------

No separate "warmup rest" duration and no per-exercise rest setting to
maintain — the rest field and the ±15s nudge are the whole control surface,
which is deliberate since this widget is used under time pressure between sets.
