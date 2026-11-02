Exercise library
==================

The exercise library is the shared vocabulary that templates, workouts,
and analytics all key off of — every set logged in the app's history
points back to one row here, which is what makes "graph Bench Press over
time" a simple query instead of a fuzzy text match.

Exercise templates
--------------------

Every exercise in the app is either an ``ExerciseTemplate`` (see the
:ref:`model-exercisetemplate` table) — sourced from the bundled dataset
submodules (RepDB and the original exercises-dataset, below) — or a
``CustomExerciseTemplate`` (:ref:`model-customexercisetemplate`) —
authored by a user from scratch. The two are separate tables, in separate
databases (see :doc:`../data_model`'s "Database split" — the catalog is
shared, common to every user; a custom exercise is this user's own), but
present one seamless interface everywhere a reader of this page would
notice: there's no create-or-reuse decision, no separate per-user
exercise row a template gets "created into" first — picking either kind
from the catalog and logging a set against it is the same single action.
(This page's "catalog" has also, at different points in the project's
history, meant a single merged table with a nullable per-user link, and
later a single table with an ``is_custom`` flag — see :doc:`../review`
for both changes and why each happened; neither is the current shape.)

- **Browsing**: the exercise picker and the bottom-nav exercise library
  page both search the same catalog (dataset-sourced + custom templates
  together), filterable by this app's own ``MuscleGroup`` — a real column
  on every template (``muscle_group_id``), not a translation done at
  query time. Selecting any result — dataset-sourced or custom, logged
  before or not — just uses that template directly; there's no
  create-or-reuse decision to get wrong.
- **Two data sources, augmented not replaced**: the catalog is built from
  `RepDB <https://repdb.co>`_ (609 exercises, clean two-pose illustrations,
  tips, muscle data) *and* the original `exercises-dataset
  <https://github.com/hasaneyldrm/exercises-dataset>`_ (1,324 exercises, one
  grainy thumbnail each), both as git submodules. Wherever RepDB covers an
  exercise — matched by the hand-reviewed ``seed_data/repdb_mapping.json``
  for the exercises you actually use, or automatically when the two names
  are the exact same set of words ("dumbbell bent over row" = "Bent-Over
  Dumbbell Row") — its images, steps, tips and muscles are used and the
  original's image stays only as a fallback. Everything RepDB has that the
  catalog didn't is added as a new template. Where there's no equivalent the
  original image and text are left alone. Near-matches are never linked
  automatically; the seed script prints a "possible duplicates" list instead.
- **Refreshing the datasets**: after ``git submodule update --remote`` on
  either submodule, re-run ``python3 scripts/seed_exercise_templates.py``
  (``--dry-run`` first to see what it would do). It's safe to re-run: it only
  refreshes dataset-owned fields (steps, images, tips, attribution, muscles)
  and never touches anything editable in the app — name, equipment, tracking
  type, muscle group, notes.
- **Images**: where RepDB has two poses (start and peak of the movement) the
  detail page alternates them as a 2-frame animation, one pose per second —
  or shows both side by side if the device asks for reduced motion. (RepDB's
  free tier has no real animations, and its paid-tier preview clips may not
  be used in production, so this is just the two stills.) Thumbnails use the
  first pose. Every image shows the attribution its license requires, and
  Settings → *About & credits* carries both sources' credit links.
- **Muscles worked**: each template stores its primary and secondary muscles
  exactly as its source names them (no translation between RepDB's
  anatomical names and the original dataset's coarser ones). The detail page
  shows them as chips; a muscle gets a highlighted-body thumbnail when RepDB
  ships a diagram under the same name (27 of them), and is a plain text chip
  otherwise. A custom template that isn't matched to either dataset has none of this
  source data — no image, steps, tips or muscle diagrams — and that's the *only* functional
  difference between the two kinds; filtering, editing, logging, and stats
  are otherwise symmetric.

Browsing
--------

.. image:: /_static/screenshots/exercise_library.png
   :alt: The exercise library's search and filter screen
   :width: 360px
   :align: center

``/exercises`` shows the **full template catalog** (all 1,324+ dataset
templates plus any custom ones), not just exercises the user has already
logged — searchable by name and filterable by muscle group. The search is
fuzzy, not a strict substring match: word order doesn't matter ("press
bench" finds "Bench Press"), and a single typo in a word is tolerated
("suqat" still finds "Squat") — see :doc:`../api/exercise_templates`. Both
the exercise library and the "add exercise" picker (template editor and
active workout) search this same way, since they call the same endpoint.
Tapping any
row goes straight to its :ref:`features/exercise_library:Exercise detail`
page — history, chart, and PRs if it's been logged before, or an empty
detail page (image + instructions, no history yet) if it's never been
used. Browsing the catalog is therefore also how a user adds an exercise
to a future workout without being mid-workout.

Custom exercises
------------------

Users can add their own from the exercise picker's "Create '<query>'"
affordance when a search has no match — required fields are just name,
muscle group, and tracking type (see :ref:`data_model:Set tracking
types`). This creates a ``CustomExerciseTemplate`` row (this user's own
database — see :doc:`../data_model`'s "Database split"), not a dataset
one; it has no dataset metadata (instructions, images, tips) to begin
with, rather than having it stripped. Everywhere else in the app —
browsing, logging, history, stats — a custom exercise behaves exactly
like a dataset-sourced one; the one real difference beyond metadata is
that a custom exercise is fully this user's own to edit or delete (see
"Editing/deleting" below), where a dataset-sourced one isn't.

Exercise detail
------------------

.. image:: /_static/screenshots/exercise_detail.png
   :alt: An exercise's detail screen, with history and progress chart
   :width: 360px
   :align: center

``/exercises/:id`` combines two things, matching Strong's exercise detail
screen — ``?custom=1`` on the URL for a custom exercise, since an id alone
doesn't say which table it's in (see :doc:`../data_model`'s "Database
split"; every in-app link to this page already appends it correctly):

- **History**: every past set for this exercise, most recent first,
  grouped by workout date.
- **Progress chart**: see :doc:`history_and_analytics`.

Editing/deleting
------------------

The only exercise edit the UI currently exposes, for either kind, is the
"Note for every workout" field (:doc:`workout_logging`) — a dataset-sourced
exercise's note is this user's own (:ref:`model-catalogexercisenote`, kept
separate from the shared row it's attached to — see :doc:`../data_model`'s
"Database split"), edited the exact same way a custom exercise's own
``notes`` field is, so the distinction is invisible here. There is
no "rename this exercise"/"delete this exercise" screen yet; the API
underneath already supports the rest of a **custom** exercise's fields
(name, muscle group, equipment, tracking type) being edited, and the
exercise deleted outright (blocked with ``409`` if it has any logged
sets — see :ref:`data_model:Business rules`), but nothing in the app
calls those endpoints today. A **dataset-sourced** exercise's other
fields (name, equipment, ...) were never user-editable even before this
split, and now additionally can't be, by design — it's shared, common
data every future user would see the same row of; the API's ``DELETE``
for one always refuses, and its ``PATCH`` only ever accepts ``notes``.
Removing or renaming a dataset exercise for real means fixing the
underlying dataset submodule or ``seed_data/`` override and re-seeding.
