Docs/code consistency review
===============================

This project is built docs-first: these documents define expected
behavior, and the implementation is checked against them rather than the
other way around. Reviews are recorded here chronologically so drift is
visible.

.. list-table::
   :widths: 15 15 70
   :header-rows: 1

   * - Date
     - Scope
     - Findings & resolution
   * - 2026-09-27
     - Initial docs pass (this document set)
     - Docs written first, no implementation yet to compare against. Baseline for the next review, once the backend/frontend/import exist.
   * - 2026-09-27
     - Post-build review (backend, frontend, and the ``.ods`` import all complete): an independent agent review plus manual browser testing of every page in both light and dark mode, dev and production (single Waitress process) serving modes.
     - Manual browser testing caught and fixed 3 frontend bugs: the workout header's Finish button was clipped off-screen at common phone widths (420px) — fixed with a proper flex layout; the progress chart's X-axis tick labels overlapped illegibly with a full multi-year history and the Y-axis's first digit was clipped by a too-aggressive negative margin — fixed with ``interval``/``minTickGap`` and a corrected margin; the exercise library and picker grouped exercises by muscle group in arbitrary (alphabetical-by-first-exercise) order instead of the intended ``display_order`` — fixed by sorting groups explicitly. The independent review found 4 more: ``Push Up``/``Chest Dip`` were mis-seeded as ``weight_reps`` instead of ``bodyweight_reps`` (a handful of weighted-vest sessions in the source history tripped the mechanical column-inference rule) — corrected in ``exercises.json`` and documented as a hand-reviewed exception in :doc:`data_migration`; ``GET /api/workouts`` was documented as supporting date-range filtering but didn't implement it — added; starting a workout from a template with a rep-range target like ``"8-12"`` silently dropped the reps pre-fill to null while weight still pre-filled — fixed to pre-fill the low end of the range; and finishing/discarding a workout didn't explicitly clear the rest timer, leaving a harmless but real stale ``localStorage`` key per workout — fixed by calling ``clear()`` in both handlers. All fixes covered by new regression tests (backend test count 35 → 38); re-verified via the full browser smoke test afterward with zero console errors.
   * - 2026-09-27
     - Added the ongoing Strong CSV import path (``scripts/import_strong_csv.py``) — the first real usage of an "incremental" importer, as opposed to the ``.ods`` importer's one-shot design.
     - Live-caught bug, not a pre-planned test: the importer's skip-if-date-exists dedup rule assumes one workout per calendar day, which broke on first real run because a throwaway "Test" workout (created earlier this session while browser-testing the active-workout screen, zero real sets) already occupied that day's date slot and silently blocked that day's real Strong session from importing. Fixed by deleting the empty test workout and re-running the import; documented as a known sharp edge in :doc:`data_migration` rather than over-engineering multi-workout-per-day handling for what should be a rare collision. Also corrected a real data error the CSV exposed: ``Goblet Squat`` had been seeded with a guessed ``dumbbell`` equipment value, but the user's actual logged sets are with a kettlebell — the importer's equipment-reconciliation step (trusts Strong's value over the spreadsheet-era guess) fixed it automatically. 3 new exercises hand-added to ``exercises.json`` for names with no reasonable existing match. Post-import browser verification then caught a more serious pre-existing bug, only ever exposed once real kg-denominated data existed: every weight column (``WorkoutSet.weight``, ``Workout.body_weight``, ``TemplateExercise.target_weight``, ``BodyweightEntry.weight``) was declared ``Numeric(6, 2)`` — fine for lbs, which nobody logs beyond 1 decimal place, but silently truncating Strong's higher-precision kg values (e.g. ``61.23492`` truncated to ``61.23``) on every read. That small a loss doesn't matter in kg, but the kg→lbs display conversion amplifies it enough to be visibly wrong: a lift the user actually did at a clean 135 lbs displayed as ``134.99 lbs``. Root-caused by comparing the raw SQLite file contents (full precision, since SQLite doesn't itself enforce column precision/scale) against what the API actually returned (truncated) — the truncation was happening in SQLAlchemy's read path, not storage. Fixed by widening all four columns to ``Numeric(8, 4)`` via an Alembic migration (SQLite ``batch_alter_table``, verified zero data loss across all 2480 sets). A second, related but separate bug in the same area: the frontend's set-editing UI (``SetRow``) never converted a stored weight into the user's display unit at all — it showed the raw stored number next to whatever unit label the *global* setting happened to be, which was only ever correct by coincidence (100% of prior data being lbs already). Fixed with a client-side ``convertWeight`` helper mirroring the backend's, wired into ``SetRow``, ``setSummary``, and the Settings body-weight list. 9 new regression tests added across both fixes (backend test count 38 → 47); full docs rebuild clean (0 warnings) and re-verified in-browser after, including the exact previously-wrong value now showing correctly.
   * - 2026-09-27
     - Backfilled real names/timestamps (``scripts/backfill_workout_names.py``) into the 201 spreadsheet-era workouts, using the same full-history Strong CSV, since ``import_strong_csv.py`` only ever adds new workouts and never touches ones that already existed.
     - Deliberately scoped to 3 workout-level fields only (``name``, ``started_at``, ``completed_at``), explicitly not touching ``WorkoutExercise``/``WorkoutSet``, specifically to avoid clobbering any set the user might have hand-edited through the app since the original import — a real risk a full re-import from the CSV would have carried, that a targeted backfill doesn't. Caught and fixed one idempotency bug in the process: the first run correctly reported 0 already-correct entries, but a second identical run *also* reported re-timing all 205 workouts, indicating the "already correct" check wasn't actually working. Root cause: SQLite always hands back naive ``datetime`` objects through SQLAlchemy regardless of a column's ``DateTime(timezone=True)`` declaration, so comparing the freshly-fetched (naive) value against the timezone-aware value computed from the CSV was structurally *always* unequal — harmless (re-writing an identical value), but meant the script wasn't honestly idempotent as documented. Fixed by comparing naive-vs-naive. Verified: 205/205 workouts renamed away from generic "Workout" on the real database (29 distinct real names), zero data loss, re-run now correctly reports 0/0/205. 4 new regression tests (backend test count 47 → 51); re-verified in-browser across the full history list, old and new entries both.

How to run a review
----------------------

1. Re-read :doc:`data_model`, :doc:`api/index`, and :doc:`features/index`
   against the current ``backend/app/models``, ``backend/app/routes``, and
   ``frontend/src``.
2. Check the domain sanity of each feature independently of the docs —
   does this still make sense for an actual training log app, not just
   "does it match what's written."
3. Record any drift or domain issues found as a new dated row above, plus
   whether it was fixed by updating the code or by updating the docs
   (docs win when the code diverged accidentally; docs get corrected when
   they specified something that turned out not to make sense in
   practice).
