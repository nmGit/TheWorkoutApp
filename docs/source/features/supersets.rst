Supersets
==========

Two or more exercises done back to back, as one round, instead of
finishing all of one's sets before starting the next. A superset of
more than two is sometimes called a "giant set"; this app doesn't draw
a line between the two names — any contiguous run of linked exercises
works the same way.

.. image:: /_static/screenshots/superset.png
   :alt: Two linked exercises in the template editor, joined by a vertical bar
   :width: 360px
   :align: center

Linking exercises
-----------------------

Open an exercise card's "⋯" menu — in the template editor and on the
active workout screen alike — and choose **"Superset with next"** to
link it with the exercise directly below it. The same menu entry
becomes **"Remove from superset"** once they're linked, to undo it.
This is a deliberate action behind a menu, not something a stray tap
can trigger, since forming or breaking a link also changes set counts
(below).

Linking is **chainable**: once A and B are linked, linking B and C
joins C into the same superset rather than breaking A and B apart to
form a new pair — repeating this down a run of adjacent exercises
builds one growing giant set. Linking two exercises that are each
already the end of their own separate chain merges both chains into
one.

Once linked, a thin blue bar appears along the **left** edge of every
member's card, running continuously across the whole group — so a
superset visually reads as one connected block, with a break in the
bar only where a superset actually starts or ends, never between two
of its own members. The bar is purely an indicator: it's never shown
for an exercise that isn't actually part of a superset, and tapping it
does nothing.

Only **adjacent** exercises can be linked — there's no "jump down the
list and pair with something three cards away." If you want to link
exercises that aren't next to each other, reorder them first (drag
handle), then link.

Forced equal set counts
--------------------------

Once exercises are linked, every member always has the same number of
sets:

- **In a template**, that's the **Sets** count (working sets) in the
  per-exercise counters — editing one member's count updates every
  other member automatically. Warm-up and drop counts stay independent
  per exercise (see :doc:`progressive_overload`), since those are
  naturally exercise-specific.
- **In an active or completed workout**, that's the actual number of
  logged sets. Tapping "+ Add set" on any member adds a set to every
  member; deleting a set from one removes the matching set (same
  position) from the rest. Linking an exercise into a group that
  already has more sets immediately pads the shorter one(s) up to
  match.

This is enforced by the server, not just nudged by the UI — even a
request built some other way can't leave a superset's members with
different set counts.

Reordering and removing
--------------------------

Dragging an exercise away from its group — or dragging something else
into the middle of it — un-links it from whichever side it's no longer
adjacent to; a superset only exists while its members are next to each
other. Removing one exercise from the superset (via "Remove from
superset", or by deleting it from the workout entirely) takes just that
one exercise out: the rest of the group, on either side, stays linked
to each other if it's still two or more members, or dissolves back to
a plain, unlinked exercise if removing that one left it down to a
single member. Removing the *middle* exercise of a 3+ chain this way
splits it into two separate, independent superset groups rather than
dissolving the whole thing, as long as each side still has two or more
members left.

Saving a workout as a template (see :doc:`templates`) carries superset
grouping over, so a chain you built live stays linked in the template
it becomes.

API
---

See :doc:`../api/workouts` (``POST .../exercises/link``, and the
``superset_group`` field on exercises) and :doc:`../api/templates` for
the endpoint-level detail, and :doc:`../data_flow` for exactly how
linking, reordering and set changes keep a superset's membership and
set counts consistent.
