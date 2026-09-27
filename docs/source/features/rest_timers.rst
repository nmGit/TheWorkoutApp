Rest timers
============

The rest timer is what makes logging *during* a workout viable instead of
reconstructing it from memory afterward — it needs to survive
interruptions (locking the phone, switching apps, an accidental refresh)
without the lifter having to think about it.

Behavior
--------

- **Auto-starts** the moment a set is marked ``completed`` (see
  :doc:`workout_logging`). Duration = the exercise's
  ``default_rest_seconds`` if set, else the global default from
  ``UserSettings``.
- Rendered as a persistent bar/sheet anchored to the bottom of the active
  workout screen: countdown (``mm:ss``), a progress ring/bar, ``-15s`` /
  ``+15s`` adjustment buttons, and a skip button.
- Starting a new set's timer while one is already running **replaces** it
  (does not stack) — only one rest timer is meaningful at a time.
- On expiry: a notification sound plus (where the browser grants
  permission) a system notification, so the lifter doesn't have to keep
  the tab in view. The bar stays visible in an "elapsed since rest ended"
  state (counting up in a muted color) rather than disappearing, since
  going a little over is normal and useful to see at a glance.
- **Survives reloads**: the running timer's end-timestamp is persisted to
  ``localStorage`` (keyed by the active workout id) the moment it starts.
  On load, the app computes remaining time from the stored end-timestamp
  rather than resuming a stored countdown — this makes it correct even if
  the tab was fully closed and reopened after the timer would have
  finished.
- Finishing or discarding the workout clears any running timer.

Configuration
--------------

- Global default lives in Settings (:doc:`bodyweight_and_settings`),
  seeded to 90 seconds.
- Per-exercise override lives on ``Exercise.default_rest_seconds``,
  editable from the exercise detail screen — e.g. compound lifts default
  higher (Strong-style convention: ~2-3 min) than isolation/accessory work
  (~60-90s). The importer in :doc:`../data_migration` does not attempt to
  infer this from history and leaves it null (falls back to global
  default) for all seeded exercises; the user tunes it over time.
- The ``-15s``/``+15s`` adjustment during an active timer is a one-off
  nudge for that set only and does not change the configured default.

Non-goals
---------

No per-set custom duration picker beyond the ±15s nudge, and no separate
"warmup rest" duration — keeping the control surface small is deliberate,
since this widget is used under time pressure between sets.
