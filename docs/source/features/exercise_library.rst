Exercise library
==================

The exercise library is the shared vocabulary that templates, workouts,
and analytics all key off of (``ExerciseTemplate.id``) — every set logged
in the app's history points back to one row here, which is what makes
"graph Bench Press over time" a simple query instead of a fuzzy text
match.

Exercise templates
--------------------

Every exercise in the app **is** an ``ExerciseTemplate`` (see the
:ref:`model-exercisetemplate` table) — either sourced from the bundled
dataset submodules (RepDB and the original exercises-dataset, below) or
authored by a user from scratch. There is no separate per-user exercise row that a
template gets "created into" — picking a template from the catalog and
logging a set against it are the same action on the same row. (This used
to be a two-row design, with a nullable link between them; see
:doc:`../review` for the bug that caused and :doc:`../data_migration` for
the merge that fixed it.)

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

``/exercises`` shows the **full template catalog** (all 1,324+ dataset
templates plus any custom ones), not just exercises the user has already
logged — searchable by name and filterable by muscle group. Tapping any
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
types`). This creates a custom ``ExerciseTemplate`` (``is_custom: true``)
directly — the same kind of row a dataset-sourced exercise is, just
without dataset metadata. Custom exercises behave identically to
dataset-sourced ones everywhere else in the app.

Exercise detail
------------------

``/exercises/:id`` combines two things, matching Strong's exercise detail
screen:

- **History**: every past set for this exercise, most recent first,
  grouped by workout date.
- **Progress chart**: see :doc:`history_and_analytics`.

Editing/deleting
------------------

Name, muscle group, equipment, and tracking type are all editable after
creation, for both dataset-sourced and custom templates — editing never
touches the dataset-only fields (instructions, image, ``body_part``,
etc.), so there's nothing to accidentally corrupt. Deleting is blocked by
the API if the template has any logged sets (see :ref:`data_model:Business
rules`) — the UI surfaces this as "used in N workouts, can't delete"
rather than a generic error — and separately blocked for any
dataset-sourced template regardless of history, since deleting one would
remove it from the catalog entirely rather than just from the user's own
history.
