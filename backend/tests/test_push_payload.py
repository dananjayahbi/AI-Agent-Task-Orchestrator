"""MT-5.4-02 — Minimal push payloads (ids and short title only).

Section 9.8 verbatim: "Payload contains only ids and a short title;
sensitive text is fetched in-app after unlock" (Section 14.2's deep
link needs routing ids only; Section 12.4: pushes are not a leak
channel). This suite pins the allowlist builder's contract:

* the exact five-field set per trigger — event type, ``project_id``,
  ``task_id``, ``task_version`` (the state version MT-5.4-03's dedupe
  key reads), and the short title;
* **excluded fields never appear even when the source trigger carries
  them** — WP-3.9 rule details, feedback, notes, evidence, diffs,
  reason codes; the allowlist copies named fields only, so event
  growth cannot leak (the blocklist-rot risk note);
* the dedupe-key and deep-link fields MT-5.4-03/WP-5.9 read are
  present — no more;
* size sanity and the truncation policy: the title is truncated to a
  prefix of the user's own text (never substituted, never appended),
  and the whole payload stays far under FCM's data ceiling.

Run with ``pytest backend/tests -k push_payload -q``.
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.notifications.payloads import (
    PUSH_PAYLOAD_FIELDS,
    PUSH_PAYLOAD_MAX_BYTES,
    PUSH_TITLE_MAX_CHARS,
    build_push_payload,
    payload_within_size_limit,
    truncate_title,
)

# A Section 9.6-ish trigger as the dispatcher fires it (Section 9.8 seam).
_BASE_TRIGGER: dict[str, Any] = {
    "event_type": "review.requested",
    "project_id": "PID00001",
    "task_id": "PID00001-T001",
    "state_version": 4,
    "reason_code": "auto_verdict_failed",  # rides the trigger; never the payload
}

# Every sensitive field the plan names, plus the trigger's own extras —
# the exclusion table the AC asserts against, fed in deliberately.
_SENSITIVE_TRIGGER: dict[str, Any] = {
    **_BASE_TRIGGER,
    "execution_summary": "the agent printed the secret into the log",
    "latest_feedback": "auditor: revert the auth change",
    "notes": "internal: the client's staging password is hunter2",
    "evidence": [{"command": "cat ~/.ssh/id_rsa", "exit_code": 0}],
    "commands": ["git push --force"],
    "diff_text": "+password = 'hunter2'",  # pragma: allowlist secret
    "attachment_text": "the design mockup with the unreleased feature",
    "policy_rule_results": {"R3": "critical_patch"},
    "free_text": "arbitrary event content",
}


def test_payload_is_exactly_the_allowlisted_field_set() -> None:
    """Section 9.8: ids + short title — the set is closed and named."""
    payload = build_push_payload(_BASE_TRIGGER, title="Fix login redirect")
    assert set(payload) == {
        "event_type",
        "project_id",
        "task_id",
        "task_version",
        "title",
    }
    assert set(payload) == set(PUSH_PAYLOAD_FIELDS)


def test_payload_values_round_trip_the_routing_ids() -> None:
    """Strings per FCM data maps; the state version survives str() casing."""
    payload = build_push_payload(_BASE_TRIGGER, title="Fix login redirect")
    assert payload["event_type"] == "review.requested"
    assert payload["project_id"] == "PID00001"
    assert payload["task_id"] == "PID00001-T001"
    assert payload["task_version"] == "4"  # MT-5.4-03's dedupe key half
    assert payload["title"] == "Fix login redirect"


def test_sensitive_fields_never_appear_even_when_the_trigger_carries_them() -> None:
    """The blocklist-rot defense: an allowlist builder cannot leak extras."""
    payload = build_push_payload(_SENSITIVE_TRIGGER, title="Escalation")
    assert set(payload) == set(PUSH_PAYLOAD_FIELDS)
    serialized = repr(payload)
    for forbidden in (
        "execution_summary",
        "latest_feedback",
        "notes",
        "evidence",
        "commands",
        "diff_text",
        "attachment_text",
        "policy_rule_results",
        "free_text",
        "reason_code",
        "hunter2",  # the content itself, not just the key
    ):
        assert forbidden not in serialized, forbidden


def test_reason_code_rides_the_trigger_but_not_the_payload() -> None:
    """The dispatcher's reason code is server-side context, not banner text."""
    payload = build_push_payload(_BASE_TRIGGER, title="Escalation")
    assert "reason_code" not in payload
    assert "auto_verdict_failed" not in repr(payload)


def test_title_truncation_is_a_prefix_never_substitution() -> None:
    """Truncate for display: the prefix of the user's own text, no marker."""
    long_title = "A" * (PUSH_TITLE_MAX_CHARS + 40)
    truncated = truncate_title(long_title)
    assert truncated == "A" * PUSH_TITLE_MAX_CHARS
    assert long_title.startswith(truncated)
    # Short titles pass through untouched — truncation only ever shortens.
    assert truncate_title("short") == "short"
    payload = build_push_payload(_BASE_TRIGGER, title=long_title)
    assert payload["title"] == truncated
    assert "…" not in payload["title"] and "..." not in payload["title"]


def test_payload_stays_well_under_the_fcm_data_ceiling() -> None:
    """Size sanity (the AC): max title, max ids — still tiny vs 4 KB."""
    big_trigger = {
        "event_type": "x" * 64,
        "project_id": "P" * 64,
        "task_id": "T" * 64,
        "state_version": 2**31,
    }
    payload = build_push_payload(big_trigger, title="Z" * 4096)
    assert payload_within_size_limit(payload) is True
    limit_probe = {key: "x" * PUSH_PAYLOAD_MAX_BYTES for key in PUSH_PAYLOAD_FIELDS}
    assert payload_within_size_limit(limit_probe) is False


@pytest.mark.parametrize(
    ("trigger", "title"),
    [
        (_BASE_TRIGGER, "Escalation for review"),
        ({**_BASE_TRIGGER, "event_type": "merge_failed"}, "Merge conflict"),
        ({**_BASE_TRIGGER, "event_type": "task.transitioned"}, "Retry exhausted"),
    ],
)
def test_snapshot_per_trigger_type(trigger: dict[str, Any], title: str) -> None:
    """One payload shape for every Section 9.8 trigger — ids and title only."""
    payload = build_push_payload(trigger, title=title)
    assert payload == {
        "event_type": trigger["event_type"],
        "project_id": "PID00001",
        "task_id": "PID00001-T001",
        "task_version": str(trigger["state_version"]),
        "title": title,
    }
