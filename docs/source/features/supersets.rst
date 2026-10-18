Supersets
==========

Two exercises done back to back, as one round, instead of finishing all of
one's sets before starting the other.

.. image:: /_static/screenshots/superset.png
   :alt: Two linked exercises in the template editor, joined by a vertical bar
   :width: 360px
   :align: center

Linking two exercises
-----------------------

Open an exercise card's "⋯" menu — in the template editor and on the
active workout screen alike — and choose **"Superset with next"** to pair
it with the exercise directly below it. The same menu entry becomes
**"Remove from superset"** once they're linked, to undo it. This is a
deliberate action behind a menu, not something a stray tap can trigger,
since forming or breaking a pair also changes set counts (below).

Once linked, a thin blue bar appears along the **left** edge of both
cards, running continuously from one into the other — so a superset
visually reads as one connected block, not two separate exercises that
happen to be next to each other. The bar is purely an indicator: it's
never shown for an exercise that isn't actually part of a pair, and
tapping it does nothing.

Only **adjacent** exercises can be linked — there's no "jump down the
list and pair with something three cards away." If you want to pair
exercises that aren't next to each other, reorder them first (drag
handle), then link.

A superset is always exactly **two** exercises, not a longer "giant set"
chain. Linking a third exercise onto either end of an existing pair
breaks that pair first and forms a new one with whichever two you just
connected — pairing is always a fresh choice, never an accumulating
chain.

Forced equal set counts
--------------------------

Once two exercises are linked, they always have the same number of sets:

- **In a template**, that's the **Sets** count (working sets) in the
  per-exercise counters — editing one member's count updates the other
  automatically. Warm-up and drop counts stay independent per exercise
  (see :doc:`progressive_overload`), since those are naturally
  exercise-specific.
- **In an active or completed workout**, that's the actual number of
  logged sets. Tapping "+ Add set" on either member adds a set to both;
  deleting a set from either removes the matching set (same position)
  from the other. Linking two exercises that already have different set
  counts immediately pads the shorter one up to match.

This is enforced by the server, not just nudged by the UI — even a
request built some other way can't leave a superset's two members with
different set counts.

Reordering and removing
--------------------------

Dragging an exercise away from its partner — or dragging something else
in between them — un-pairs it; a superset only exists while its two
members are next to each other. Removing one member of a pair (not the
whole workout, just that exercise) simply leaves the other on its own,
unlinked.

Saving a workout as a template (see :doc:`templates`) carries superset
pairing over, so a linked pair you built live stays linked in the
template it becomes.

API
---

See :doc:`../api/workouts` (``POST .../exercises/link``, and the
``superset_group`` field on exercises) and :doc:`../api/templates` for
the endpoint-level detail, and :doc:`../data_flow` for exactly how
linking, reordering and set changes keep a pair's membership and set
counts consistent.
