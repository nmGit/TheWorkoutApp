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

Browsing
--------

``/exercises`` — searchable by name, filterable by muscle group and
equipment. Each row shows the exercise name and, if it has history, the
date and result of the last time it was logged.

Custom exercises
------------------

Users can add their own (``is_custom: true``) from the exercise picker's
"Create '<query>'" affordance when a search has no match — required
fields are just name, muscle group, and tracking type (see
:ref:`data_model:Set tracking types`). Custom exercises behave identically
to seeded ones everywhere else in the app.

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
