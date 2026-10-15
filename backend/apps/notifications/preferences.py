"""Per-event-type notification preferences — storage-side logic (MT-5.4-05).

Section 9.8's trigger set as *preference types* (Section 14.1's "per-event-type
toggles", Section 13.1's "notification preferences"), with OQ-13's decided
default honored: **per-event toggles only; the completion digest off by
default**, escalations on so FR-MOB-04 works out of the box.

**Trigger → preference-key mapping (recorded ruling, WP-5.4 changelog).**
Section 9.8 lists four triggers — "``in_human_review`` entry (all reasons),
merge failure, retry exhaustion, and the optional digest of completions" —
while every push physically arrives through the one dispatcher seam
(``trigger_review_push`` on ``in_human_review`` entry, WP-5.4's wiring).
Each trigger resolves to **exactly one** preference key so disabling a type
leaves the others untouched (the MT's isolation requirement):

* reason ``retry_exhausted`` (T9) → ``retry_exhaustion``;
* a merge-failure row (T18: event ``merge.failed`` / reason ``merge_failed``)
  → ``merge_failure``;
* every other ``in_human_review`` entry (T8/T10/T14, ...) →
  ``in_human_review`` — the "all reasons" umbrella;
* ``completion_digest`` is stored and exposed but never consulted: OQ-13
  keeps the digest unbuilt (building it is a separate task).

"The plan gives toggles for event types without carving out mandatory ones"
(MT risk note) — this module therefore *never* hard-codes a type as
un-muteable: defaults are on, every type stays toggleable, and the mandatory-
escalation policy question stays open rather than silently answered.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import PREFERENCE_EVENT_TYPES, NotificationPreference

#: The Section 9.8 preference set — the closed list every surface reads
#: (MT-5.9-03 shows exactly these as toggles; no type may be invented).
NOTIFICATION_EVENT_TYPES: tuple[str, ...] = PREFERENCE_EVENT_TYPES

#: OQ-13 defaults: escalations on (FR-MOB-04 out of the box), digest off.
DEFAULT_ENABLED: dict[str, bool] = {
    "in_human_review": True,
    "merge_failure": True,
    "retry_exhaustion": True,
    "completion_digest": False,
}


def resolve_preference_key(trigger: Mapping[str, Any]) -> str:
    """One dispatch trigger → its Section 9.8 preference key (the ruling above).

    Falls back to ``in_human_review`` for anything unrecognized — the
    umbrella entry trigger is the only sensible default (never the digest:
    an unknown push must not silently ride the off-by-default type).
    """
    event_type = str(trigger.get("event_type", ""))
    reason = str(trigger.get("reason_code", ""))
    if event_type in ("merge.failed", "merge_failed") or reason == "merge_failed":
        return "merge_failure"
    if reason == "retry_exhausted":
        return "retry_exhaustion"
    return "in_human_review"


def get_or_create_preference(event_type: str) -> NotificationPreference:
    """The stored row for [event_type], created with its OQ-13 default."""
    return NotificationPreference.objects.get_or_create(
        event_type=event_type,
        defaults={"enabled": DEFAULT_ENABLED[event_type]},
    )[0]


def ensure_preference_rows() -> list[NotificationPreference]:
    """Materialize all four rows (the GET path) in declared order."""
    return [get_or_create_preference(key) for key in NOTIFICATION_EVENT_TYPES]


def preference_enabled_for_key(event_type: str) -> bool:
    """Current switch for one preference key (materializes on first read)."""
    return get_or_create_preference(event_type).enabled


def preference_enabled(trigger: Mapping[str, Any]) -> bool:
    """Consultation entry point for the dispatch path (Section 9.8 flow).

    Called **after trigger selection and before dedupe/send** (MT-5.4-05's
    Scope): a disabled type produces zero FCM attempts and touches neither
    the dedupe nor the tracking tables — nothing recorded means the
    Section 17 success-rate metric cannot be skewed by muted types (the
    MT's ordering risk note). There is no queue anywhere: a disabled
    trigger's dispatch simply returns, so re-enabling later notifies only
    events dispatched after the change (no retro-fire by construction).
    """
    return preference_enabled_for_key(resolve_preference_key(trigger))


__all__ = [
    "DEFAULT_ENABLED",
    "NOTIFICATION_EVENT_TYPES",
    "ensure_preference_rows",
    "get_or_create_preference",
    "preference_enabled",
    "preference_enabled_for_key",
    "resolve_preference_key",
]
