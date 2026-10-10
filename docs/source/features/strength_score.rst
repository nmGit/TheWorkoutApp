Strength score
==============

Each workout is scored against your usual strength, muscle by muscle. A score
of **1.0** means no change, **above 1.0** means stronger than usual, and
**below 1.0** means weaker. The score answers "am I stronger than before?",
not "did I do more work?". Total volume isn't used.

Current method
--------------

This section describes the method the app uses now (``services/generated_v2.py``).
The sections after it describe the previous method, kept for comparison.

- **Each exercise has its own baseline**, built only from its sessions in the last
  180 days, weighted by 0.5 ** (days ago / 21). Exercises are never pooled, so swapping
  exercises doesn't move a muscle's score on its own. A baseline needs three sessions
  in the window; otherwise the exercise has no baseline yet.
- **Each exercise's session value** is the mean of its best three counting sets
  from that session only (estimated one-rep max for lifts, duration for holds).
- **Likely entry errors are set aside.** A session more than 60% away from its
  baseline (or, with no baseline, more than 60% above the exercise's best so far) is
  not scored and doesn't feed later baselines. This catches entries such as a 753 lb
  incline bench.
- **Each exercise's change** is the log of its session value minus the log of its
  baseline.
- **Each muscle's change** is the average of its exercises' changes, weighted by each
  exercise's share for that muscle times its counting sets (the **evidence**), and
  pulled towards zero by a shrinkage of one set's worth: change × evidence /
  (evidence + 1). Thin evidence gives a small change.
- **Workout score** is the geometric mean of the muscle ratios.
- **Effort** is generated, not entered: a counting set is "hard" when its estimated
  reps in reserve is 3 or less, based on the exercise's earlier best. Hard-set counts
  are kept as generated data but aren't used in the score yet.
- **Counting sets** have 1–15 reps. Sets from 1 to 8 reps count fully, and sets above
  8 count less, falling to half weight at 15.
- A muscle that is worked but has no scored exercise yet shows as "no baseline", and
  a planned muscle that hasn't been worked yet shows as "pending". Both are blue on
  the body map, so a workout still shows the muscles it covers. Muscles the workout
  doesn't touch are grey.

Previous method (for comparison)
--------------------------------

Exercises only report. An exercise contributes which muscles it works and its
sets. The score never looks at an exercise's own history, so a new exercise
counts from its first session.

Per-set input
-------------

A set counts toward strength only if all of these hold:

- it is **completed**;
- it is **not a warm-up** and **not a drop set**;
- it has a weight above zero, in ``lbs`` or ``kg`` (converted to kg);
- it has between **1 and 10 reps**.

Each counting set has an estimated one-rep max, using the Epley formula
(``WorkoutSet.estimated_one_rm``): ``load × (1 + reps / 30)``, or the load
itself for a single.

Two kinds of measurement are scored, each with its own baseline per muscle so the
scales never mix:

- **load** (``weight_reps`` exercises): the estimated one-rep max above, in kg.
- **hold** (``time`` exercises): how long a set lasted, in seconds. A plank is scored
  this way. Stretches in the Mobility group are timed but aren't strength work, so
  they're left out.

Cardio is never scored. Bodyweight-reps exercises aren't scored yet either, because
their logged weight is zero and there's no load to estimate from.

For a hold set, the metric is ``duration_seconds`` (with the same completed, not
warm-up, not drop-set rules). The top-3 selection and muscle weights below apply to
holds in the same way, ranked by duration.

Muscle weights
--------------

Each exercise distributes its sets across the muscles it works:

- **primary** muscles: weight **1.0**;
- **secondary** muscles: weight **0.5**;
- a muscle listed as both is primary.

Each exercise's muscle weights are then scaled to add up to 1. That gives each muscle
its **share** of the exercise's work. A bench press with chest 1.0 and triceps 0.5
has shares of 2/3 for the chest and 1/3 for the triceps. A muscle's credit from a set
is that set's metric (estimated 1RM, or duration for holds) multiplied by its share, so
a lift's full weight is never credited to every muscle it works.

Muscle names are canonicalised first (see ``canonical_muscle_slug``), so
``biceps`` and ``biceps_brachii`` are the same muscle.

Per-muscle value for one workout
--------------------------------

For each muscle and each kind of measurement (load, hold), take the **top 3**
credited sets (the metric multiplied by the muscle's share) across the exercises
in that workout that work it. The muscle's value is their mean, weighted
by each set's muscle weight:

.. math::

   V_m = \frac{\sum_{s \in \text{top 3}} e_s \cdot w_{s,m}}{\sum_{s \in \text{top 3}} w_{s,m}}

Taking the top sets, rather than all of them, means extra volume or a fatigued
finish doesn't pull the value down. The value tracks peak capacity.

Worked example (triceps, one workout): bench 100 kg × 5 twice (e1RM 117, share 1/3,
credit 39.0 each), bench 95 kg × 8 (e1RM 120, credit 40.1), pushdown 40 kg × 10
(e1RM 53, share 1, credit 53.3). Sorted, the credits are 53.3, 40.1, 39.0, 39.0. The
top three are 53.3, 40.1 and 39.0, so the triceps value for this workout is 44.1 kg.
The top three are chosen from this workout's sets only. Earlier workouts are used
only in the baseline.

Baseline
--------

Each muscle has an exponential moving average of its past values, with span
``N = 5``:

.. math::

   \alpha = \frac{2}{N + 1} = \frac{1}{3}, \qquad
   B_m \leftarrow \alpha V_m + (1 - \alpha) B_m

Baselines are built from completed workouts that started before the one being
scored, oldest first. A muscle's baseline is first set from its first value.

Score
-----

Each muscle and kind has a ratio ``V_m / B_m``, computed **before** the workout is
folded into the baseline. A muscle's ratio is the geometric mean of its kinds'
ratios, so a muscle worked by a lift and by a hold is scored on both.

The workout score is the **geometric mean** of its muscles' ratios. A +20%
muscle and a -20% muscle cancel to 0.96, so 1.0 really means no net change.

Warm-up period
--------------

A muscle is scored only after it has **at least 3 earlier workouts** with data
for it. Before that, it's shown as *no baseline* (grey), and the workout score
is ``null`` until at least one muscle is scored.

Colours on the workout map
--------------------------

Each body region is coloured by the muscle or muscles that map to it (see
``frontend/src/lib/muscleMap.ts``):

- **Green to red**: the ratio. Full colour at ±10% (``SATURATION = 0.1``), and
  neutral near 1.0. If several muscles share a region, their ratios are
  averaged geometrically.
- **Blue**: planned or skipped. The region belongs to an exercise in the
  workout with no completed set yet, and no counting set in this workout
  works it.
- **Grey**: no data. This covers regions no exercise works, and muscles still
  in their warm-up period.

Completed work takes priority over blue, so a region worked by both a completed
and a pending exercise is coloured by its score.

API
---

``GET /api/workouts/<id>/strength``
   Returns ``score`` (a number, or ``null``) and ``muscles``, keyed by canonical
   slug. Each entry has a ``status`` of ``scored``, ``no_baseline``, or
   ``pending``, and a ``ratio`` (set only when ``scored``).

The score is computed on each request by replaying the completed workouts
before the target. Nothing is stored.

Decisions still open
--------------------

- **RPE:** sets have an ``rpe`` field. A reps-in-reserve estimate could replace
  Epley when it's logged. Not used yet.
- **Exercise mix:** an e1RM from one exercise is on a different scale from
  another's, so swapping exercises can shift a muscle's value. Accepted for now.
- **Muscle weights:** 1.0 and 0.5 are assumptions. They should be checked against
  your own history.
