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

#: The Section 9.8 preference set — the closed list of toggleable event
#: types (MT-5.4-05; MT-5.9-03 shows exactly these). Lives here so the
#: model's choices and :mod:`apps.notifications.preferences` cannot drift.
PREFERENCE_EVENT_TYPES: tuple[str, ...] = (
    "in_human_review",
    "merge_failure",
    "retry_exhaustion",
    "completion_digest",
)


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


class NotificationPreference(models.Model):
    """One per-event-type notification switch (Section 9.8; MT-5.4-05).

    **Account-level, not per-device** (the MT's risk note: storage
    granularity is unset by the plan — account-level fits both named
    surfaces, Section 13.1 web settings and Section 14.1 mobile toggles,
    which edit the *same* record): like MT-5.4-01's fan-out, this is a
    single-owner product, so there is no user/owner foreign key to hang the
    rows on — one row per Section 9.8 preference type, unique on
    ``event_type``.

    Defaults are applied where rows are created (``preferences.
    get_or_create_preference``): escalations on, completion digest off
    (OQ-13). Rows hold no payload or task content (Section 12.4: this table
    is not a leak channel either).
    """

    event_type = models.CharField(
        max_length=64,
        unique=True,
        choices=[(key, key) for key in PREFERENCE_EVENT_TYPES],
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Identify the switch without any content beyond type + state."""
        return f"notification-preference:{self.event_type}:{self.enabled}"
