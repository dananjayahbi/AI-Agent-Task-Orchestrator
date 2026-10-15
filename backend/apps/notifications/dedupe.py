"""The dedupe check-and-record for the push dispatch job (MT-5.4-03).

The Section 9.8 key `(event type, task id, state version)` scoped per
device. :func:`claim_dedupe` is an **insert-first** claim: the atomic
``INSERT`` (unique constraint on :class:`~apps.notifications.models.PushDedupeRecord`)
decides the winner, so two concurrent workers processing one trigger
cannot both send — no read-then-write window (Section 18 concurrency
posture; the ADR-012 idempotency posture applied to push dispatch).
``IntegrityError`` *is* the "already claimed" answer, not a failure.

Where the check sits (the MT's scope): between trigger evaluation and
the sender call inside :func:`apps.notifications.dispatch.dispatch_push`
— after the fan-out selects a device, before one FCM attempt. A
retried job, a re-delivered event, or a worker restart mid-dispatch
re-derives the same key and loses the claim: one push per device per
key, by construction.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.accounts.models import Device

from .models import PushDedupeRecord


def claim_dedupe(device: Device, *, event_type: str, task_id: str, state_version: int) -> bool:
    """Atomically claim (device, event type, task id, state version).

    ``True`` — this process now owns the send for that device+key;
    proceed to the sender. ``False`` — another worker (or an earlier
    attempt of this one) already claimed it; suppress, never send.

    The insert runs in its own savepoint so the ``IntegrityError``
    never poisons an outer transaction the job may be wrapped in.
    """
    try:
        with transaction.atomic():
            PushDedupeRecord.objects.create(
                device=device,
                event_type=event_type,
                task_id=task_id,
                state_version=state_version,
            )
    except IntegrityError:
        return False
    return True


__all__ = ["claim_dedupe"]
