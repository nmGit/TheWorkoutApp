API reference
=============

All endpoints are mounted under ``/api``, accept/return JSON, and use
standard HTTP status codes (``200``/``201`` success, ``400`` validation
error, ``404`` not found, ``409`` conflict — e.g. starting a second active
workout). Timestamps are ISO 8601 UTC. Decimal fields (weight, distance)
are transmitted as JSON numbers.

.. toctree::
   :maxdepth: 1

   exercises
   templates
   workouts
   stats
   settings
