"""The notifications persistence models (Section 9.8; MT-5.4-03/04).

* :class:`PushDedupeRecord` — the MT-5.4-03 per-device dedupe key
  (event type, task id, state version), unique-constrained so
  check-and-record is one atomic insert (Section 18 concurrency
  posture; the ADR-012 idempotency posture applied to push).
* :class:`PushDeliveryRecord` — the MT-5.4-04 per-send delivery
  status (outcome, attempts, FCM error classification), aligned to the
  same event key and storing **no payload content** (Section 12.4:
  neither table may become a leak channel — ids and verdicts only).

Both are operational data with a ``created_at`` retention anchor —
the recorded 90-day window and cleanup entry points live in
:mod:`apps.notifications.tracking` (flagged for owner confirmation in
the WP changelog).
"""

from __future__ import annotations

from django.db import models

from apps.accounts.models import Device


class DeliveryOutcome(models.TextChoices):
    """The sender's three-valued verdict, persisted (MT-5.4-01)."""

    ACCEPTED = "accepted", "Accepted"
    TRANSIENT_FAILURE = "transient_failure", "Transient failure"
    PERMANENT_FAILURE = "permanent_failure", "Permanent failure"


class PushDeliveryRecord(models.Model):
    """One device's send outcome for one Section 9.8 event key."""

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="push_delivery_records",
    )
    # The MT-5.4-03 key, verbatim — tracking and dedupe stay aligned.
    event_type = models.CharField(max_length=64)
    task_id = models.CharField(max_length=64)
    state_version = models.PositiveIntegerField()
    # The per-token send-loop verdict and its evidence — never the payload.
    outcome = models.CharField(max_length=24, choices=DeliveryOutcome.choices)
    attempts = models.PositiveIntegerField()
    error_code = models.CharField(max_length=64, blank=True)
    invalid_token = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """Identify the row without any payload content (Section 12.4)."""
        return (
            f"push-delivery:{self.device_id}:{self.event_type}:"
            f"{self.task_id}:{self.state_version}:{self.outcome}"
        )


class PushDedupeRecord(models.Model):
    """One (device, event type, task id, state version) — sent or claimed."""

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="push_dedupe_records",
    )
    # Section 9.8's key, verbatim — three fields, none added.
    event_type = models.CharField(max_length=64)
    task_id = models.CharField(max_length=64)
    state_version = models.PositiveIntegerField()
    # Retention anchor (this task's recorded choice — see the WP
    # changelog): cleanup reads created_at, never a TTL column.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["device", "event_type", "task_id", "state_version"],
                name="push_dedupe_unique_device_key",
            )
        ]

    def __str__(self) -> str:
        """Identify the row without any payload content (Section 12.4)."""
        return f"push-dedupe:{self.device_id}:{self.event_type}:{self.task_id}:{self.state_version}"
