Body weight & settings
========================

Body weight log
------------------

A simple date + weight log, independent of workouts (``BodyweightEntry``,
one entry per day — logging again on the same day replaces that day's
entry rather than adding a second one). Lives on the **home dashboard**,
under "Recent workouts", not in Settings — it's something you add to
regularly, unlike a preference you set once.

- An input + "Log" button records today's weight. The weight is only
  cleared from the box once the save actually succeeds; a failed save
  (network blip, server hiccup) leaves the box as you typed it and shows
  a visible error, rather than clearing as if it had worked with nothing
  actually saved. (Earlier builds cleared it unconditionally — see
  :doc:`../review`.)
- The latest entry is shown with a quick "Delete" (undoable for a few
  seconds, like other deletes in the app).
- Older entries are shown as a trend **chart** rather than a list, once
  there are at least two of them; with only one entry, a short message
  explains there's nothing to chart yet.

Included in the product because the source workout history already
contains a body-weight-adjacent signal, and relative-strength context
(e.g. "your squat is now 1.5x bodyweight") is a natural, low-cost
extension once both numbers exist — computed the same on-read way as
other stats, not stored.

Settings
--------

.. image:: /_static/screenshots/settings_menu.png
   :alt: The Settings menu
   :width: 300px
   :align: center

``/settings`` is a short menu of sections rather than one long page, each
holding part of the single ``UserSettings`` row:

- **General** (``/settings/general``):

  .. image:: /_static/screenshots/settings_general.png
     :alt: The General settings page
     :width: 300px
     :align: center


  - **Units**: weight (lbs/kg) and distance (mi/km). Changes the
    *display* and the unit new entries are recorded in; never rewrites
    historical values (see :ref:`data_model:Business rules`).
  - **Theme**: system, light, dark, green, or pink.
  - **Default rest timer** duration, used when a set has no rest history
    to suggest one yet (see :doc:`rest_timers`).

- **Generated Workouts** (``/settings/generated-workouts``): everything
  to do with progressive overload — progression method, default rep
  range, experience, and load step. See :doc:`progressive_overload` for
  what each one does; this page is also where :doc:`generated_workouts`'s
  panel options would live if they became persistent preferences (they
  aren't yet — count/stretching/cardio/familiar-first are chosen fresh
  each time you open the panel).
- **About & credits** (``/settings/about``): the exercise data sources'
  attribution (RepDB, exercises-dataset).

Each section page has a "← Settings" link back to the menu. There is no
account/profile section — v1 is single-user with no auth (see
:ref:`overview:Non-goals`), so Settings is purely app preferences.
