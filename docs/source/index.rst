WorkoutApp
==========

WorkoutApp is a self-hosted strength-training tracker: log workouts as you lift,
build reusable routine templates, run rest timers between sets, and review
progress over time. It is heavily inspired by `Strong
<https://www.strong.app/>`_, adapted to a self-hosted React + Python stack
and seeded with the author's own multi-year lifting history.

This documentation is written **before** the corresponding code and is the
source of truth for how the application should behave. When the
implementation and these docs disagree, that is a bug in one of the two —
see :doc:`review` for how that's tracked.

.. toctree::
   :maxdepth: 2
   :caption: Product

   overview
   features/index
   data_migration

.. toctree::
   :maxdepth: 2
   :caption: Engineering

   architecture
   data_model
   api/index
   review

.. toctree::
   :maxdepth: 1
   :caption: Appendix

   glossary
