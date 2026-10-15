"""Minimal push payload builder (Section 9.8; MT-5.4-02).

Section 9.8 verbatim: "Payload contains only ids and a short title;
sensitive text is fetched in-app after unlock." Section 14.2: the tap
deep-links to the task's review sheet *after unlock*, so the payload
needs routing data and nothing else; Section 12.4: pushes must never
become a leak channel — the one display string allowed is the short
task title so the OS banner is meaningful.

**Allowlist, never blocklist** (the MT's risk note):
:func:`build_push_payload` copies exactly the five named fields —
event type, ``project_id``, ``task_id``, ``task_version`` (the state
version MT-5.4-03's dedupe key needs) and the title — from whatever
the trigger carries. WP-3.9's rule details, feedback, notes, diffs,
evidence and any future event growth cannot leak, because nothing
unlisted is ever read. Widening the set is a plan change against
Section 9.8 (the contract), not a code change.

**Truncation policy** (the AC): the title is truncated for display at
:PUSH_TITLE_MAX_CHARS characters — display-time shortening, never
substitution, never appended content (no ellipsis injected: the
truncated string is a prefix of the user's own text, full stop). All
values are strings (FCM data maps carry strings), which keeps the
message far inside OS banner limits; the documented bound is checked
by :func:`payload_within_size_limit` — the FCM v1 data-payload ceiling
is 4 KB and this builder's output is orders of magnitude below it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

#: The Section 9.8 field set — ids plus the short title, nothing else.
#: Exported so tests assert the exact allowlist, not a copy of it.
PUSH_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {
        "event_type",
        "project_id",
        "task_id",
        "task_version",
        "title",
    }
)

#: Display truncation for the OS banner — a short, human glanceable
#: line, not a paragraph (Section 9.8 "a short title"). Truncation is
#: a display policy: the payload carries the prefix of the real title.
PUSH_TITLE_MAX_CHARS = 64

#: FCM v1's documented data-payload ceiling; the sanity check stays an
#: order of magnitude below it.
PUSH_PAYLOAD_MAX_BYTES = 4096


def truncate_title(title: str) -> str:
    """Truncate the title for display; never substitute or append.

    A prefix of the user's own text — no ellipsis marker (adding
    characters would be content the author did not write; the client
    renders the banner and can style the cut itself).
    """
    return title[:PUSH_TITLE_MAX_CHARS]


def build_push_payload(trigger: Mapping[str, Any], *, title: str) -> dict[str, str]:
    """One trigger plus the short title → the minimal Section 9.8 payload.

    *trigger* is the dispatcher's ``trigger_review_push`` payload
    (event type, project id, task id, ``state_version``); *title* is
    the task's short title fetched by the dispatch job. Only the
    :data:`PUSH_PAYLOAD_FIELDS` names are copied — ``reason_code``
    rides the trigger today and is deliberately **not** forwarded
    (the reason is server-side context; the banner says what needs
    routing, not why — Section 9.8, Section 12.4).
    """
    return {
        "event_type": str(trigger["event_type"]),
        "project_id": str(trigger["project_id"]),
        "task_id": str(trigger["task_id"]),
        "task_version": str(trigger["state_version"]),
        "title": truncate_title(title),
    }


def payload_within_size_limit(payload: Mapping[str, str]) -> bool:
    """The payload-size sanity check (the AC): UTF-8 bytes under the bound."""
    return len(json.dumps(dict(payload)).encode("utf-8")) <= PUSH_PAYLOAD_MAX_BYTES


__all__ = [
    "PUSH_PAYLOAD_FIELDS",
    "PUSH_PAYLOAD_MAX_BYTES",
    "PUSH_TITLE_MAX_CHARS",
    "build_push_payload",
    "payload_within_size_limit",
    "truncate_title",
]
