"""Section 9.9's push-dispatch job (WP-5.4; ADR-003; NFR-03).

**Worker-side only (Section 9.8).** The dispatcher fires the in-process
``trigger_review_push`` seam *inside* the dispatch transaction; that
seam only *enqueues* — :func:`enqueue_push_dispatch` registers a
``transaction.on_commit`` callback that hands the trigger payload to
the Celery task (the events publisher's exact posture: the worker must
never see a row the web process has not committed). The task body,
:func:`dispatch_push`, runs in the worker, fans out to active devices
and invokes the retrying sender in :mod:`apps.notifications.sender`.
Nothing here batches or delays the first attempt — dispatch starts on
event (NFR-03's 10-second window).

**Fan-out decision (recorded for the WP changelog).** The plan gives
no project→owner link on the ``Project`` model, and the product is
single-owner (Section 12.2 "Owner login"), so the MT-5.4-01 fan-out is
*every active device* — ``revoked_at IS NULL`` with a non-empty push
token, revoked rows excluded by the lost-phone control (ADR-006).
MT-5.4-05's preferences refine *whether* a device is targeted; the
per-device dedupe in MT-5.4-03 refines *how often* — neither changes
this selection.

**Trigger selection (MT-5.4-01 scope).** All triggers are active from
the start, as the MT fixes: the ``in_human_review`` entry seam the
dispatcher already fires covers "in_human_review entry (all reasons)"
and, by the same hook, T9's retry exhaustion; merge failure and retry
exhaustion reach the same seam via their review-requested entries
(T18; WP-3.7 wiring). MT-5.4-05 inserts its preference filter as a
downstream step here, never at the seam.

**Payload minimization** (Section 9.8: "ids and a short title") is
MT-5.4-02's :func:`apps.notifications.payloads.build_push_payload` —
this job fetches the task's short title and hands the trigger to the
allowlist builder; the payload can carry nothing the Section 9.8 field
set does not name, however events grow (WP-3.9 rule details ride the
event stream, never the push).

**Dedupe** (Section 9.8: "per-device dedupe key (event type, task id,
state version) prevents duplicates on retries") is MT-5.4-03's
:func:`apps.notifications.dedupe.claim_dedupe` — an atomic insert-first
claim between device selection and the send, so retried jobs,
re-delivered events and mid-dispatch worker restarts yield one push
per device per key.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from celery import shared_task
from django.db import transaction

from apps.accounts.models import Device
from apps.tasks.models import Task

from .dedupe import claim_dedupe
from .payloads import build_push_payload
from .sender import send_to_token
from .tracking import prune_invalid_token, record_delivery

type PushTrigger = Mapping[str, Any]


def active_devices() -> list[Device]:
    """Devices this job fans out to — the lost-phone control applied.

    A revoked device (Section 12.1) stops receiving push on the very
    same query that guards its authentication (ADR-006); a device row
    with an empty token can never be a valid FCM destination and is
    skipped defensively rather than raising at send time.
    """
    return list(
        Device.objects.filter(revoked_at__isnull=True).exclude(push_token="").order_by("pk")
    )


def task_short_title(task_id: str) -> str:
    """The task's short title for the banner — server-fetched, never in the trigger.

    The trigger rides the in-process seam with ids only (Section 9.8);
    the title is data the worker loads itself. A missing row (deleted
    between trigger and worker) yields an empty banner line rather than
    a crash — the ids still route the deep link in-app.
    """
    return Task.objects.filter(pk=task_id).values_list("title", flat=True).first() or ""


def dispatch_push(trigger: PushTrigger) -> dict[str, int]:
    """Fan out one committed trigger to every active device (the job body).

    Per device: **dedupe claim first** (MT-5.4-03 — the Section 9.8
    ``(event type, task id, state version)`` key, atomic insert, one
    send per device per key even across retries and worker restarts),
    then build the Section 9.8 minimal payload (MT-5.4-02's allowlist
    builder — ids plus the short title) and run the retrying sender
    once. Every send records a delivery row (MT-5.4-04 — ids, outcome,
    attempts, FCM classification, never payload); a definitive
    invalid-token verdict prunes the token so future dispatches skip
    the device. The return value counts outcomes (``accepted`` /
    ``transient_failed`` / ``permanent_failed`` / ``suppressed``) —
    the same numbers :func:`apps.notifications.tracking.push_success_stats`
    aggregates from the persisted rows.
    """
    summary = {
        "accepted": 0,
        "transient_failed": 0,
        "permanent_failed": 0,
        "suppressed": 0,
    }
    data = build_push_payload(trigger, title=task_short_title(str(trigger["task_id"])))
    for device in active_devices():
        claimed = claim_dedupe(
            device,
            event_type=data["event_type"],
            task_id=data["task_id"],
            state_version=int(trigger["state_version"]),
        )
        if not claimed:
            summary["suppressed"] += 1
            continue
        result = send_to_token(device.push_token, data)
        record_delivery(
            device,
            event_type=data["event_type"],
            task_id=data["task_id"],
            state_version=int(trigger["state_version"]),
            outcome=result.outcome,
            attempts=result.attempts,
            error_code=result.error_code,
            invalid_token=result.invalid_token,
        )
        if result.invalid_token:
            # Section 9.8 "invalid push tokens are pruned" — only on the
            # sender's definitive flag (ambiguous codes never prune).
            prune_invalid_token(device)
        if result.outcome == "accepted":
            summary["accepted"] += 1
        elif result.outcome == "transient_failure":
            summary["transient_failed"] += 1
        else:
            summary["permanent_failed"] += 1
    return summary


@shared_task(name="notifications.dispatch_push")  # type: ignore[untyped-decorator]
def dispatch_push_task(trigger: dict[str, Any]) -> dict[str, int]:
    """The worker entry point (ADR-003): one trigger, one fan-out."""
    return dispatch_push(trigger)


def enqueue_push_dispatch(trigger: PushTrigger) -> None:
    """The ``trigger_review_push`` hook body: enqueue after commit.

    Registered process-wide by :func:`ensure_push_dispatch_wired`. The
    snapshot is a plain dict — the Celery serializer carries no ORM
    objects (the worker re-queries devices itself).
    """
    if not trigger:
        return
    snapshot = dict(trigger)
    transaction.on_commit(lambda: dispatch_push_task.delay(snapshot))


def ensure_push_dispatch_wired() -> bool:
    """Install the push dispatch on the Section 9.8 review-push seam.

    Returns whether the real hook was installed. Two documented gates:
    the unit layer (``apps.core.settings.test``) stays hermetic — no
    broker, and existing suites keep their exact ``pushes == []``
    assertions (the attachments ``install_pipeline_enqueue_seam``
    precedent); and push-disabled deployments (the default) skip
    entirely, so a stack with no FCM project runs clean (MT-5.4-01's
    risk note).
    """
    if os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".test"):
        return False
    from django.conf import settings

    if not settings.PUSH_ENABLED:
        return False
    from apps.tasks.state_machine.hooks import set_review_push_hook

    set_review_push_hook(enqueue_push_dispatch)
    return True


__all__ = [
    "active_devices",
    "dispatch_push",
    "dispatch_push_task",
    "enqueue_push_dispatch",
    "ensure_push_dispatch_wired",
    "task_short_title",
]
