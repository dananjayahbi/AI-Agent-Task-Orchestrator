"""The two narrow in-process seams later WPs plug into (MT-1.5-01/03).

**Event seam (Section 8.2 rule 2; Section 9.6).** Every dispatch calls
``emit_transition_event`` *inside* the open transaction with the
Section 9.6 envelope fields (``type``, ``project_id``, ``task_id``,
``occurred_at``, ``actor``, ``data``). WP-1.9's write-in-transaction
helper (MT-1.9-02) registers the real Event-row writer as the
**default** with ``set_default_event_hook`` from its app config
(``EventsConfig.ready()``); until an events app is configured the
default is ``None`` and the seam is a no-op. ``set_event_hook`` is the
*test* override on top of that default: install a recorder (or ``None``
to clear it), and dispatches fall back to the production writer —
``reset_hooks`` in the WP-1.5 suites therefore means "the seam runs as
production does", not "the seam is dead". This is the plan's *single*
in-transaction event hook — MT-1.5-01's risk note forbids inventing a
second event mechanism (recorded as an open-question candidate in the
WP changelog; resolved by this default/override split). The hook must
never touch the network (MT-1.9-02: Redis publishing happens
post-commit); ``id`` and ``correlation_id`` are the helper's to fill.

**Review-push seam (Section 9.8).** The dispatcher calls
``trigger_review_push`` when a transition lands the task in
``in_human_review`` — Section 9.8's "in_human_review entry (all
reasons)" trigger (which also covers T9's retry exhaustion; the dedupe
key ``event type, task id, state version`` rides the payload). WP-5.4
registers the FCM dispatcher with ``set_review_push_hook``; this module
performs no delivery, only the in-process trigger (MT-1.5-03 scope).

**Review-requested rule-details seam (WP-3.9; MT-3.9-01/02).** The
dispatcher emits exactly one ``review.requested`` Event row on every
``in_human_review`` entry, carrying the canonical ``review_reason`` and
``task_version``; the Policy Engine's persisted rule results ride along
only where an engine decided (T14) — the audit app registers the
reader of ``policy_rule_results`` with
``set_default_review_rule_details_hook`` from
``AuditConfig.ready()``; rows without a policy evaluation (T8/T9/T18)
express absence by the empty mapping, never a fabricated rule set.

Both hooks replaceable: ``set_event_hook`` layers a test recorder over
the production default (cleared with ``None``), and
``set_review_push_hook(None)`` restores the no-op push seam — test
fixtures observe emissions without touching production wiring.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

type EventHook = Callable[[Mapping[str, Any]], None]
type ReviewPushHook = Callable[[Mapping[str, Any]], None]
#: MT-3.9-01: the rule-details half of the ``review.requested`` ``data``
#: payload — ``(task, transition_id)`` in, the Policy Engine's persisted
#: ``policy_rule_results`` mapping (WP-3.4's shape) out; empty mapping
#: when the row carried no policy evaluation (T8/T9/T18 by design —
#: absence is expressible, never fabricated).
type ReviewRuleDetailsHook = Callable[[Any, str], Mapping[str, Any]]

_default_event_hook: EventHook | None = None
_event_hook: EventHook | None = None
_review_push_hook: ReviewPushHook | None = None
_default_review_rule_details_hook: ReviewRuleDetailsHook | None = None
_review_rule_details_hook: ReviewRuleDetailsHook | None = None


def set_default_event_hook(hook: EventHook | None) -> None:
    """Install (or remove) the production Event-row writer (WP-1.9).

    Called once from ``apps.events.apps.EventsConfig.ready()`` with
    ``apps.events.services.write_transition_event`` — the seam's
    baseline for every dispatch outside tests.
    """
    global _default_event_hook
    _default_event_hook = hook


def set_event_hook(hook: EventHook | None) -> None:
    """Override the in-transaction Event-row writer (test seam).

    ``None`` clears the override so dispatch falls back to the
    production default (WP-1.9's writer), not to a no-op.
    """
    global _event_hook
    _event_hook = hook


def emit_transition_event(payload: Mapping[str, Any]) -> None:
    """Write one Event row in the caller's transaction — override, else default."""
    hook = _event_hook if _event_hook is not None else _default_event_hook
    if hook is not None:
        hook(payload)


def set_review_push_hook(hook: ReviewPushHook | None) -> None:
    """Install (or remove) the Section 9.8 push dispatcher (WP-5.4)."""
    global _review_push_hook
    _review_push_hook = hook


def trigger_review_push(payload: Mapping[str, Any]) -> None:
    """Signal an ``in_human_review`` entry for push — no delivery here."""
    if _review_push_hook is not None:
        _review_push_hook(payload)


def set_default_review_rule_details_hook(hook: ReviewRuleDetailsHook | None) -> None:
    """Install (or remove) the Policy Engine's rule-details provider (WP-3.9).

    Called once from ``apps.audit.apps.AuditConfig.ready()`` with the
    reader of the persisted ``policy_rule_results`` (MT-3.9-01's rule
    details); until an audit app is configured the default is ``None``
    and ``review.requested`` payloads carry the reason without rule
    details (MT-3.9-02: absence is expressible, never fabricated).
    """
    global _default_review_rule_details_hook
    _default_review_rule_details_hook = hook


def set_review_rule_details_hook(hook: ReviewRuleDetailsHook | None) -> None:
    """Override the rule-details provider (test seam); ``None`` clears it."""
    global _review_rule_details_hook
    _review_rule_details_hook = hook


def review_rule_details(task: Any, transition_id: str) -> Mapping[str, Any]:
    """The ``review.requested`` data additions for one entry — override, else default."""
    hook = (
        _review_rule_details_hook
        if _review_rule_details_hook is not None
        else _default_review_rule_details_hook
    )
    if hook is None:
        return {}
    return hook(task, transition_id)
