Data flow
==========

How entered data (what a user types) turns into generated data (what the
app computes) for each major feature, end to end. See
:doc:`glossary` for the entered/generated distinction and
:doc:`data_model` for the schema these flows read and write.

Starting a workout from a template
------------------------------------

``POST /api/workouts {template_id}`` (``routes/workouts.py:start_workout``):

1. Reject with 409 if a workout is already active
   (``Workout.completed_at IS NULL``).
2. Create the ``Workout`` (name copied from the template) and, for each
   ``TemplateExercise`` in position order, a ``WorkoutExercise``.
3. For each one, ``services/sets_plan.py:plan_sets(template_exercise)``.
   ``plan_sets`` only reads ``exercise_id``/``target_reps``/``warmup_sets``/
   ``target_sets``/``drop_sets`` off whatever it's given, so a caller with
   no ``TemplateExercise`` (generated workouts, step 10 below) passes a
   plain ``SetPlanSpec`` with the same fields instead:

   a. Load ``UserSettings`` (progression method, load step, weight unit).
   b. Find that exercise's most recent **completed** session
      (``WorkoutExercise`` joined to a completed ``Workout``, newest
      first) and split its sets into warm-up/working/drop by
      ``is_warmup``/``is_dropset``.
   c. Resolve the rep range: the template exercise's own ``target_reps``
      if set, else ``UserSettings.default_rep_range``, parsed by
      ``parse_rep_range`` (``"8-12"`` → ``(8, 12)``; anything unparseable
      falls back to ``(8, 12)``).
   d. ``progress_working(working_sets, rep_range, settings)`` — see
      :ref:`data_flow:Progressive overload calculation` below — returns
      either a single ``(weight, unit, reps)`` to apply to every working
      set, or ``None`` (progression off, or no earlier logged weight to
      work from).
   e. Build one dict per planned set, in warm-up → working → drop order:
      a warm-up/drop set copies the same-kind set at the same position
      from last session (or the last one of that kind, if there were
      fewer last time; or nothing, if there's no history at all) and is
      marked ``is_progressed: False``; a working set uses the
      ``progress_working`` result and is marked ``is_progressed: True``
      if there is one, else it also just copies last time's (also
      ``False`` — a copy is never "progressed", even for a working set).
4. ``sets_plan.py:make_planned_sets`` turns each dict into an unsaved
   ``WorkoutSet`` with ``completed: false`` and its values written to
   ``planned_weight``/``planned_weight_unit``/``planned_reps``/
   ``planned_duration_seconds``/``planned_is_progressed`` — **not** to
   ``weight``/``reps``/``duration_seconds``. Those stay null until the set
   is actually completed, at which point ``planned_is_progressed`` is
   reset to ``False`` along with the rest (see "Completing a set" below).
   This same pairing (build a spec, call ``plan_sets``, then
   ``make_planned_sets``) is also what generated workouts use (step 10
   below) — it's the one place a workout's starting sets are ever built.

Progressive overload calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``sets_plan.py:progress_working``, given last session's working sets:

1. Off → ``None`` immediately.
2. No working set with a logged, positive weight → ``None`` (nothing to
   progress from; the planned-set builder falls back to a plain copy).
3. Convert every working set's weight to kg, find the top weight, and
   take every set within 0.5% of it as "the top sets" (handles a session
   logged as, say, 100.0 and 99.98 due to a unit round-trip).
4. ``reached`` = every top set's reps were at or above the range's high
   end.
5. **Linear**: reached → top weight + load step, reps = range high.
   Not reached → same weight, same reps target (range high).
6. **Double**: reached → top weight + load step, reps = range low (reset
   to the bottom of the range at the new weight). Not reached → same
   weight, reps = one more than the top sets' lowest rep count (capped
   to the range).
7. Convert the result back to the user's display unit and round to 2
   decimals.

Completing a set
------------------

``PATCH /api/sets/:id {completed: true, ...}`` (``routes/workouts.py:update_set``):

1. Apply every field present in the request body to the row as given
   (this can include real ``weight``/``reps`` the user typed).
2. If the set is *newly* completed (wasn't before, is now): for each of
   ``weight``+``weight_unit``, ``reps``, ``duration_seconds`` still null
   after step 1, copy it from the matching ``planned_*`` column. Then
   null out all four ``planned_*`` columns and reset
   ``planned_is_progressed`` to ``False``.
3. Commit.

This is why a set can be completed with the checkmark alone, with nothing
typed: whatever was planned becomes real at that moment. It's also why a
set can never show both a real and a planned value for the same field —
step 2 always clears the planned ones.

Generating a workout
----------------------

``POST /api/workouts/generated {count, stretching, cardio, familiar_first, groups}``
(``routes/workouts.py:create_generated`` → ``services/generate.py:plan``):

1. Reject with 409 if a workout is already active (same rule as starting
   from a template).
2. ``services/recency.py:days_since_trained(today)`` — the one place this
   is computed — returns, per canonical muscle slug, days since the most
   recent completed, non-warm-up, non-drop-set, non-stretch working set
   that worked it. A muscle never trained at all is simply absent.
3. ``overdue(d) = min(d, 60) + 1`` for every muscle with a value — caps
   how much one extremely stale muscle can dominate an average.
4. ``current_days`` keeps only muscles trained within the last 60 days
   (``NEVER_DAYS``); muscles outside that window are excluded from "in
   need" counts (but a group with *no* current muscles at all is dropped
   from ranking entirely, not just discounted).
5. ``in_need`` = the subset of ``current_days`` at or past
   ``IN_NEED_DAYS`` (8).
6. ``group_scores``/``rank_groups``: each training group (the fixed
   ``GROUP_MUSCLES`` mapping — see :doc:`data_model`) gets
   ``(muscles in need, muscles current, average overdue-ness)``; groups
   are ranked by the first divided by the second (ties broken by the
   third). This is what the generate panel's chips show and
   pre-select the top two from.
7. ``focus`` = the request's ``groups`` if given (validated against
   ``GROUP_MUSCLES``), else the top ``GROUP_FOCUS`` (2) ranked groups.
8. For each of ``count`` strength picks: try each focus group in turn
   (round-robin, offset by the pick index) for an exercise that helps at
   least one muscle still in ``need`` (``_priority``: the share-weighted
   average need of the muscles it works, via
   ``strength.py:muscle_shares`` — the same primary=1.0/secondary=0.5
   weighting the strength score uses). Picking an exercise reduces the
   remaining need of the muscles it covers
   (``need[slug] *= 1 - share``), so the next pick in the same group
   tends to cover something else. If explicit ``groups`` were given, a
   group that's run out of in-need help still gets picked from (ignoring
   ``need``) rather than widening outside the chosen groups; otherwise,
   running out widens to progressively more of the ranked groups before
   finally falling back to the single most overdue exercise overall.
   ``familiar_first`` tries only already-logged exercises first, in every
   step, before falling back to the full catalog (including never-logged
   ones).
9. If ``stretching``/``cardio`` were asked for, one more pick each, from
   that pool only, by overall overdue-ness (not restricted to the chosen
   groups).
10. ``create_generated_workout`` names the workout after its strength
    exercises' groups (e.g. "Chest, Back & Legs"). For each exercise, it
    builds a ``sets_plan.SetPlanSpec`` (3 working sets for a
    ``weight_reps``/``bodyweight_reps`` exercise, 1 otherwise, no
    warm-ups/drops, no rep-range override) and runs it through the same
    ``plan_sets``/``make_planned_sets`` pair step 3 above uses — so a
    generated workout's working sets get progressive overload too, just
    always as plain working sets with the Settings default rep range
    (see :doc:`features/generated_workouts`).

Strength scoring a workout
----------------------------

``GET /api/workouts/:id/strength`` and ``GET /api/strength/history``
(``services/generated_v2.py``), computed fresh on every request —
nothing is stored:

1. Load every completed workout that started before the target (oldest
   first), plus the target itself if it's not yet completed (so an
   in-progress workout can show a live score).
2. Replay them in order through one ``V2Series``: for each workout,
   reduce every counting exercise session to one value (mean of its best
   3 counting sets, rep-weighted — see :doc:`features/strength_score`),
   compare it against that *exercise's own* baseline (a 180-day,
   21-day-half-life weighted average of its past sessions — never pooled
   with other exercises), set aside likely entry errors, then fold the
   kept sessions into the running history for the *next* workout's
   baselines.
3. Each exercise's change (log session value − log baseline) is
   distributed to its muscles by share × counting-set-count (the
   evidence), averaged per muscle and shrunk toward zero by one set's
   worth of "no change" — thin evidence moves the needle less.
4. The target workout's own point is the one actually returned; replaying
   history is how its baseline gets built without storing anything.
   ``score_series_v2`` reuses the same replay to answer "every workout's
   score" in one pass (the home screen's strength chart) without redoing
   the baseline from scratch per point.

Settings, front to back
--------------------------

- ``GET /api/settings`` is fetched once by ``api/settings.ts:useSettings``
  with ``staleTime: Infinity`` — it only changes when the app itself
  writes it, never from outside, so there's no reason to ever refetch
  speculatively.
- ``SettingsContext`` (``context/SettingsContext.tsx``) wraps the whole
  app in that query's data, falling back to hard-coded defaults
  (mirroring the backend model's own defaults) while it's still loading,
  so components don't need to null-check settings everywhere.
- Every settings page (:doc:`features/bodyweight_and_settings`) writes
  through one ``useUpdateSettings`` mutation — ``PATCH /api/settings``
  with just the changed field(s) — whose ``onSuccess`` replaces the
  cached settings object directly with the server's response rather than
  invalidating and refetching, so a change is reflected everywhere
  instantly.
- The backend validates each field independently in
  ``routes/settings.py`` (enum membership for
  theme/units/progression_method/experience, numeric bounds for the load
  steps, ``rep_range_or_none`` for ``default_rep_range``) and returns the
  full updated row.

Muscle recency and the body maps
-----------------------------------

``recency.py:last_trained_dates()`` is the single query behind three
different UI surfaces, so they can never disagree with each other:

- The home screen's recency map (:doc:`features/history_and_analytics`) —
  ``GET /api/muscles/recency``, coloured green (recent) to red (stale) to
  grey (never) by ``lib/recency.ts``.
- The generate panel's group ranking (:doc:`features/generated_workouts`)
  — ``GET /api/workouts/generate/groups``.
- The exercise library's muscle filter sort order
  (:doc:`features/exercise_library`).

Each slug's regions for the SVG come from ``muscle_regions.py``, looked
up the same way regardless of which of the three endpoints is asking.
