"""The state-machine service of the tasks app (Section 9.1; WP-1.5).

``tasks`` owns all state changes: every canonical transition of the
Section 8.2 table runs through ``dispatcher.dispatch_transition``, which
resolves the pair ``(from_state, trigger)`` against ``registry``, checks
the actor, evaluates guards, applies side effects, increments
``version``, and writes the Task Transition history row plus the
Section 9.6 event-hook call — all in one database transaction
(Section 8.2's three universal rules: illegal pairs answer
``TASK_STATE_CONFLICT``/409, one transaction writes state + Transition +
Event rows, the UI's ``version`` is checked optimistically).

Layout (one concern per file; Section 20.3):

* ``registry``     — the table *as data*: ``TransitionSpec`` and
  ``TransitionRegistry`` (the registration extension point later WPs use).
* ``loader``       — registers the WP-1.5 rows into the default registry.
* ``hooks``        — the single in-transaction event seam (WP-1.9 plugs
  the Event-row writer in; no second mechanism is invented here) and the
  narrow Section 9.8 review-push seam (WP-5.4).
* ``guards``       — shared guard helpers (lease predicates, worker
  clearing, dependency readiness) used by more than one table row.
* ``dispatcher``   — the generic execution path (resolve, actor check,
  guards, side effects, Section 8.3 invariants, history, event, push).
* ``transitions_owner`` / ``transitions_system`` / ``transitions_agent``
  — the T2/T3/T19 rows, the T5/T9 rows, and the T4/T6/T7/T8 stubs.

Later work packages extend the table **only** through
``TransitionRegistry.register(..., replace=True)`` — the dispatcher never
learns about individual rows (MT-1.5-01's extension-point requirement;
MT-1.5-04 proves it with an override test). The package init deliberately
re-exports nothing: consumers import the specific submodule so app
loading stays free of registration side effects.
"""

from __future__ import annotations
