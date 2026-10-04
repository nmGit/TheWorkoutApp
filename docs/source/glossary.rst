Glossary
========

.. glossary::

   Template
      A saved, reusable shape for a workout (exercises, order, target
      sets/reps). Called a "routine" in Strong.

   Active workout
      The single ``Workout`` row with ``completed_at IS NULL``. At most
      one may exist at a time.

   Set
      One physical set: weight×reps, a duration, or duration+distance,
      depending on the exercise's tracking type.

   Tracking type
      Which fields an exercise's sets use: ``weight_reps``,
      ``bodyweight_reps``, ``time``, or ``cardio``.

   Estimated 1RM (e1RM)
      Estimated one-rep max, via the Epley formula:
      ``weight * (1 + reps / 30)``.

   PR
      Personal record — the best-ever value of a given metric
      (max weight, e1RM, single-set volume, etc.) for an exercise.

   Volume
      weight × reps for a single set, or the sum across a workout/session
      depending on context (always specified where used).

   Drop set
      A set performed immediately after the previous one, at reduced
      weight, with no rest in between.

Entered data
   Information a user enters: workouts, sets, exercises, notes, body weight. It is
   the source of truth and can't be regenerated.

Generated data
   Information derived from entered data, such as strength scores, muscle ratios,
   baselines, and estimated effort. It's idempotent and can always be regenerated
   from entered data, so it can be recalculated when the method improves.
