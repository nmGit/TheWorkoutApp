Templates
=========

``GET /api/templates``
   List templates ordered by ``display_order``, each with its
   ``exercises`` nested (``TemplateExercise`` rows, each with the exercise
   name/id inlined so the list view needs no extra requests).

``POST /api/templates``
   Create a template. Body: ``name`` (required), ``notes``, ``exercises``
   (array of ``{exercise_id, target_sets, warmup_sets, drop_sets,
   target_reps, target_weight, superset_group}``, in order). ``target_reps``
   is this exercise's progressive-overload rep-range override (e.g.
   ``"8-12"``), not a literal per-set target — see
   :doc:`../features/progressive_overload`. ``superset_group``, set
   identically on two adjacent entries, pairs them into a
   :doc:`superset <../features/supersets>` — the server re-derives and
   enforces valid pairing from this on every save (not just taking it as
   given), including forcing both members' ``target_sets`` equal; see
   :doc:`../data_flow`.

``POST /api/templates/from-workout/:workoutId``
   Create a template from a completed workout, per
   :ref:`features/templates:Creating a template from a past workout`.

``GET /api/templates/:id``
   Full template detail.

``PATCH /api/templates/:id``
   Partial update, including replacing the ``exercises`` array wholesale
   (the editor autosaves the full ordered list on any change — simpler and
   sufficiently cheap at this scale than diffing individual reorders).

``PATCH /api/templates/reorder``
   Body: ``[{id, display_order}]`` — bulk reorder for the template list
   drag-and-drop.

``DELETE /api/templates/:id``
   Deletes the template and its ``TemplateExercise`` rows. Any
   ``Workout.template_id`` referencing it is set to null (never cascades
   into history) — see :ref:`data_model:Business rules`.
