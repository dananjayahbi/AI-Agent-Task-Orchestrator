"""The Section 9.6 event catalog — the single authoritative list of types.

The parent plan's Section 9.6 catalog is authoritative: these 24 strings
(``project.created|updated``, ``task.created|updated|transitioned|claimed|
released``, ``task.checkpoint``, ``task.lease_expiring``,
``task.lease_expired``, ``attachment.processing|ready|failed``,
``audit.claimed|passed|escalated``, ``review.requested|decided``,
``merge.started|succeeded|failed``, ``agent.session_started|ended``,
``system.alert``) are copied verbatim, in plan order. Nothing may be
added, dropped or renamed here without the catalog-first change the
global DoD demands (Section 20.4 item 5): the catalog is amended in the
plan *first*, then this tuple, then the migration's check constraint.

Consumers:

* :func:`apps.events.services.write_event` refuses any type outside
  :data:`EVENT_TYPES` — a type the catalog does not know is a
  programming error, never a silent write.
* The ``events_event`` table's ``CheckConstraint`` freezes the same set
  at the database, so the guarantee survives raw SQL too.
* ``backend/tests/events/test_event_catalog.py`` pins this tuple to an
  independently written copy of the Section 9.6 list (traceability,
  Section 20.5) and cross-checks the WP-1.5 suites' frozen twin in
  ``tests/wp15_helpers.py`` so the two lists cannot drift.
"""

from __future__ import annotations

#: Section 9.6's event catalog, verbatim and in plan order (24 types).
SECTION_9_6_EVENT_TYPES: tuple[str, ...] = (
    "project.created",
    "project.updated",
    "task.created",
    "task.updated",
    "task.transitioned",
    "task.claimed",
    "task.released",
    "task.checkpoint",
    "task.lease_expiring",
    "task.lease_expired",
    "attachment.processing",
    "attachment.ready",
    "attachment.failed",
    "audit.claimed",
    "audit.passed",
    "audit.escalated",
    "review.requested",
    "review.decided",
    "merge.started",
    "merge.succeeded",
    "merge.failed",
    "agent.session_started",
    "agent.session_ended",
    "system.alert",
)

#: Fast membership set for the writer's catalog check.
EVENT_TYPES: frozenset[str] = frozenset(SECTION_9_6_EVENT_TYPES)
