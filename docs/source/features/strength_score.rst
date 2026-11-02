Strength score
==============

Each workout is scored against your usual strength, muscle by muscle. A score
of **1.0** means no change, **above 1.0** means stronger than usual, and
**below 1.0** means weaker. The score answers "am I stronger than before?",
not "did I do more work?". Total volume isn't used.

Method
------

This is the method the app uses (``services/generated_v2.py``), which
superseded an earlier, simpler one (a single EMA baseline per muscle, no
per-exercise history) -- see :doc:`../review` for when and why.

- **Each exercise has its own baseline**, built only from its sessions in the last
  180 days, weighted by 0.5 ** (days ago / 21). Exercises are never pooled, so swapping
  exercises doesn't move a muscle's score on its own. A baseline needs three sessions
  in the window; otherwise the exercise has no baseline yet.
- **Each exercise's session value** is the mean of its best three counting sets
  from that session only (estimated one-rep max for lifts, duration for holds).
  A ``bodyweight_reps`` exercise (push-ups, pull-ups...) is scored the same way as
  a weighted lift, using your nearest logged body weight plus any added weight as
  the load — see :ref:`features/strength_score:Per-set input`.
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
- **Each exercise's own contribution** to that workout score is also reported, in
  percentage points — see :ref:`features/strength_score:Per-exercise contribution`.
- **Effort** is generated, not entered: a counting set is "hard" when its estimated
  reps in reserve is 3 or less, based on the exercise's earlier best. Hard-set counts
  are kept as generated data but aren't used in the score yet.
- **Counting sets** have 1–15 reps. Sets from 1 to 8 reps count fully, and sets above
  8 count less, falling to half weight at 15.
- A muscle that is worked but has no scored exercise yet shows as "no baseline", and
  a planned muscle that hasn't been worked yet shows as "pending". Both are blue on
  the body map, so a workout still shows the muscles it covers. Muscles the workout
  doesn't touch are grey.

Per-set input
-------------

A set counts toward strength only if all of these hold:

- it is **completed**;
- it is **not a warm-up** and **not a drop set**;
- it has an ``effective_weight`` above zero, in ``lbs`` or ``kg`` (converted to kg)
  — for a ``weight_reps`` set that's the same as its own entered weight, but for a
  ``bodyweight_reps`` set it's body weight (the nearest logged ``BodyweightEntry``,
  see below) plus that set's own weight, which is just the *added* load on top and
  is normally 0 (see ``WorkoutSet.effective_weight``);
- it has between **1 and 15** reps, at full weight through 8 and falling to half
  weight at 15 (``rep_weight``, used when picking an exercise session's top sets).

Each counting set has an estimated one-rep max, using the Epley formula
(``_estimated_one_rm_kg``): ``load × (1 + reps / 30)``, or the load itself for a
single.

Two kinds of measurement are scored, each with its own baseline per exercise so the
scales never mix:

- **load** (``weight_reps`` *and* ``bodyweight_reps`` exercises): the estimated
  one-rep max above, in kg. For a ``bodyweight_reps`` exercise (push-ups, pull-ups,
  dips...), the load isn't the set's own ``weight`` alone — it's the nearest logged
  body weight (``BodyweightEntry`` on or before the workout's date, falling back to
  the earliest one ever logged if the workout predates all of them) plus that added
  weight, since a push-up's real load is your body weight, not the usually-zero
  amount added on top of it. A ``bodyweight_reps`` exercise contributes nothing at
  all if body weight has never been logged even once — there's no load to estimate
  from — rather than scoring it as zero.
- **hold** (``time`` exercises): how long a set lasted, in seconds. A plank is scored
  this way. Stretches in the Mobility group are timed but aren't strength work, so
  they're left out.

Cardio is never scored.

Muscle weights
--------------

Each exercise distributes its sets across the muscles it works:

- **primary** muscles: weight **1.0**;
- **secondary** muscles: weight **0.5**;
- a muscle listed as both is primary.

Each exercise's muscle weights are then scaled to add up to 1. That gives each muscle
its **share** of the exercise's work. A bench press with chest 1.0 and triceps 0.5
has shares of 2/3 for the chest and 1/3 for the triceps — so a lift's full weight is
never credited to every muscle it works.

Muscle names are canonicalised first (see ``canonical_muscle_slug``), so
``biceps`` and ``biceps_brachii`` are the same muscle.

Per-exercise session value and baseline
----------------------------------------

For each exercise *block* in a workout (``WorkoutExercise``, not muscle), its
**session value** is the weighted mean of its best three counting sets, by
``rep_weight``:

.. math::

   V_e = \frac{\sum_{s \in \text{top 3}} e_s \cdot r_s}{\sum_{s \in \text{top 3}} r_s}

where :math:`e_s` is a set's estimated 1RM (or duration, for a hold) and :math:`r_s`
is its ``rep_weight``. The top three are chosen from this one session only — an
earlier session only ever feeds the *baseline* below, never this value directly.

The exercise's **baseline** is a half-life-weighted mean, on the log scale, of its
own sessions (same kind: load or hold) from the last 180 days:

.. math::

   w_i = 0.5 ^ {\,\text{days ago}_i / 21}, \qquad
   B_e = \frac{\sum_i w_i \cdot \ln V_{e,i}}{\sum_i w_i}

with at least 3 sessions in the window required, or :math:`B_e` is undefined (the
exercise has "no baseline" yet). The exercise's own **change** this session is
:math:`\ln V_e - B_e`.

Worked example (triceps, this session): a heavy bench press (change +0.03 against
its own baseline, share 1/3, 1 counting set) and a light pushdown (change +0.06, share
1, 1 counting set) both worked triceps. Evidence is :math:`\frac{1}{3} \cdot 1 \approx 0.33`
for the bench and :math:`1 \cdot 1 = 1` for the pushdown; see the next section for how
those combine.

From exercise change to muscle score
---------------------------------------

Each muscle's **change** this workout is the evidence-weighted mean of every
exercise's own change that touched it, shrunk toward zero by one set's worth of "no
change" (``SHRINKAGE = 1``):

.. math::

   C_m = \frac{\sum_e \text{evidence}_{e,m} \cdot \text{change}_e}{\sum_e \text{evidence}_{e,m} + 1},
   \qquad \text{evidence}_{e,m} = \text{share}_{e,m} \cdot \text{counting sets}_e

Continuing the worked example: triceps' change is
:math:`\frac{0.33 \times 0.03 + 1 \times 0.06}{0.33 + 1 + 1} \approx 0.03`. The
muscle's **ratio** is :math:`e^{C_m}`, reported once the muscle has at least one
exercise with a baseline (see :ref:`features/strength_score:Warm-up period`).

The workout score is the **geometric mean** of its muscles' ratios. A +20%
muscle and a -20% muscle cancel to 0.96, so 1.0 really means no net change.

Per-exercise contribution
----------------------------

Alongside the score, each exercise *block* reports its own share of it, in
percentage points — the number a badge on that exercise's card shows (e.g. ``+0.8%``
next to a workout header reading "+3.2% stronger"). It's derived by expanding the
workout score's geometric mean back out into exercise-level terms:

.. math::

   \ln(\text{score}) = \frac{1}{n}\sum_{m \,\in\, \text{scored}} C_m
   = \sum_e \text{change}_e \cdot \underbrace{\frac{1}{n}\sum_{m \,\in\, \text{scored}}
     \frac{\text{evidence}_{e,m}}{\sum_{e'} \text{evidence}_{e',m} + 1}}_{\text{exercise } e\text{'s weight}}

where :math:`n` is the number of scored muscles. This decomposition is exact (every
exercise's contribution, in percentage points, sums to :math:`\ln(\text{score}) \times
100` precisely) and additive in the same log space the ratios themselves are computed
in — close enough to :math:`(\text{score} - 1) \times 100`, the percent the header
displays, that the two read as "the same number split up" for the single-digit swings
this score actually produces. An exercise whose only muscles are still "no baseline"
or "pending" contributes nothing and is left out of the response entirely, rather
than showing a badge for zero.

Reported per ``WorkoutExercise`` id (not per exercise) — a workout with the same
exercise in two separate blocks (e.g. on both sides of a superset split, or just
added twice) gets two independent numbers, one per block, from whichever sets are
actually logged against that block.

Warm-up period
--------------

A muscle is scored only after it has **at least one exercise with a baseline**
(itself needing 3 of that exercise's own sessions in the last 180 days). Before
that, it's shown as *no baseline* (blue, same as "worked, no score yet"), and the
workout score is ``null`` until at least one muscle is scored.

Colours on the workout map
--------------------------

The body diagram is rendered by the ``@abdofallah/musclemap-js`` SVG
renderer (:doc:`../architecture`), which draws named body *regions*, not
muscles directly. ``services/muscle_regions.py`` maps each canonical
muscle slug to the region(s) it lights up (several muscles can share a
region, and the reverse); the frontend's ``lib/strengthColors.ts`` turns
each muscle's score into a colour per region:

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
   Returns ``score`` (a number, or ``null``), ``muscles`` (keyed by canonical
   slug, each entry with a ``status`` of ``scored``, ``no_baseline``, or
   ``pending``, and a ``ratio`` set only when ``scored``), and ``exercises`` --
   each contributing ``WorkoutExercise`` id (as a JSON object key, so a string)
   mapped to its own percentage-point share of ``score``; an exercise with
   nothing to contribute is left out, not listed as 0.

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
