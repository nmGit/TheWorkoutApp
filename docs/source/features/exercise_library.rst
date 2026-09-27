Exercise library
==================

The exercise library is the shared vocabulary that templates, workouts,
and analytics all key off of (``Exercise.id``) — every set logged in the
app's history points back to one row here, which is what makes "graph
Bench Press over time" a simple query instead of a fuzzy text match.

Seeded library
---------------

The app seeds with the exercise list recovered from the imported
spreadsheet (68 exercises across 8 muscle groups — see
:doc:`../data_migration`), since that list already represents a real,
used vocabulary rather than a generic 500-exercise database the user would
never fully browse. New built-in exercises can be added later the same
way (a seed migration), but the app does not ship an exhaustive generic
catalog for v1.

Exercise templates
--------------------

Every exercise in the app is created from an ``ExerciseTemplate`` (see
:ref:`data_model:ExerciseTemplate`) — a reusable blueprint that either
comes from the bundled `exercises-dataset
<https://github.com/hasaneyldrm/exercises-dataset>`_ submodule
(``external/exercises-dataset``, 1,324 exercises) or was authored by a
user as a custom exercise.

- **Browsing templates**: the exercise picker's "Browse templates" tab
  searches the dataset-sourced templates (thumbnail + name), separately
  from the user's own exercise list. Selecting one creates an ``Exercise``
  linked to that template (``Exercise.template_id``), mapping the
  dataset's body-part/equipment vocabulary onto this app's fixed
  ``MuscleGroup`` list and ``equipment`` enum
  (``app/services/exercise_templates.py``).
- **Refreshing the dataset**: after ``git submodule update --remote
  external/exercises-dataset``, re-run
  ``python3 scripts/seed_exercise_templates.py`` — it upserts by the
  dataset's own id, so it's safe to run repeatedly.
- **Image and instructions**: a template created from the dataset carries
  a thumbnail image (served from ``GET
  /api/exercise-templates/<id>/image``) and English step-by-step
  instructions (only English is imported, even though the dataset ships
  10 languages). Any exercise created from that template shows both on
  its :ref:`exercise detail page <features/exercise_library:Exercise
  detail>`, along with the dataset media's required
  ``© Gym visual`` attribution.

Browsing
--------

``/exercises`` — searchable by name, filterable by muscle group and
equipment. Each row shows the exercise's template thumbnail (if it has
one), its name, and, if it has history, the date and result of the last
time it was logged.

Custom exercises
------------------

Users can add their own from the exercise picker's "Create '<query>'"
affordance when a search has no match — required fields are just name,
muscle group, and tracking type (see :ref:`data_model:Set tracking
types`). Creating one this way also creates a matching custom
``ExerciseTemplate`` (``is_custom: true``) behind the scenes, so it
becomes a reusable template of its own, alongside the dataset-sourced
ones. Custom exercises behave identically to seeded ones everywhere else
in the app.

Exercise detail
------------------

``/exercises/:id`` combines two things, matching Strong's exercise detail
screen:

- **History**: every past set for this exercise, most recent first,
  grouped by workout date.
- **Progress chart**: see :doc:`history_and_analytics`.

Editing/deleting
------------------

Name, muscle group, equipment, tracking type, and rest-timer default are
all editable after creation. Deleting an exercise is blocked by the API if
it has any logged sets (see :ref:`data_model:Business rules`) — the UI
surfaces this as "used in N workouts, can't delete" rather than a generic
error.
