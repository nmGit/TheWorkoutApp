WorkoutApp
==========

WorkoutApp is a self-hosted strength-training tracker: log workouts as you lift,
build reusable routine templates, run rest timers between sets, generate a
workout from what's due for training, and review progress — including a
per-muscle strength score — over time. It is heavily inspired by `Strong
<https://www.strong.app/>`_, adapted to a self-hosted React + Python stack
and seeded with the author's own multi-year lifting history.

This manual is written for two different readers, in two sections:

- :doc:`the user manual <overview>` — how to use the app: every screen,
  button and setting, and the behaviors behind them. If you're looking for
  "what does this do", start there. The app itself links into specific
  pages of this section — look for a small "Help" link near the feature
  you're looking at.
- :doc:`the developer guide <architecture>` — how the app is built: the
  API, the database schema, the data flow through each major feature, and
  the code layout. For working on the app itself, not just using it.

These docs describe the app as it actually behaves. When the
implementation and these docs disagree, that's a bug in one of the two —
see :doc:`review` for how that's tracked.

.. toctree::
   :maxdepth: 2
   :caption: User Manual

   overview
   features/index
   data_migration

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   architecture
   data_model
   data_flow
   api/index
   review

.. toctree::
   :maxdepth: 1
   :caption: Appendix

   glossary
