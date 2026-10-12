"""The Device entity (parent plan Section 7.2; MT-1.2-04; ADR-006).

Section 12.2 mobile layer: after Owner login the app registers a device and
receives a device-bound token kept in client secure storage; the device is
**independently revocable** (lost-phone threat, Section 12.1). The model
carries exactly the Section 7.2 field set — ``id``, ``user_id``, ``platform``,
``push_token``, ``token_id`` (FK to the ``kind = device`` API Token),
``biometric_bound``, ``last_seen_at``, ``revoked_at`` — nothing added.

Ambiguities flagged per the MT risk note (decisions recorded in the WP
changelog, not guessed twice):

* ``platform`` vocabulary — the plan names the two mobile flavors
  (iOS/Android, Section 18/21) but pins no enum, so this model fixes the
  closed ``ios`` / ``android`` pair and the registration serializer rejects
  anything else with ``VALIDATION_ERROR``;
* ``biometric_bound`` — the plan states the *client* releases the token only
  after biometric success (Section 12.2) but not how the flag arrives;
  registration accepts it as an optional boolean (default ``false``) and the
  server merely records it — enforcement is Flutter-side (FR-MOB-06, M5).

``push_token`` is sensitive at rest (Section 12.4): it never appears in
responses (only its Device row) and the log scrubber redacts ``*_token``
keys (MT-1.1-02), so the registration payload cannot leak through the JSON
logs.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from .tokens import ApiToken


class Platform(models.TextChoices):
    """The two mobile flavors the plan ships (Section 18/21)."""

    IOS = "ios", "iOS"
    ANDROID = "android", "Android"


class Device(models.Model):
    """One registered phone/tablet bound to exactly one device token."""

    # Section 7.2 `user_id`: devices belong to the owner account (N:1).
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
    )
    platform = models.CharField(max_length=8, choices=Platform.choices)
    # Sensitive (12.4): stored for push dispatch (WP-5.x), never returned.
    push_token = models.TextField()
    # Section 7.2 `token_id`: the device-bound credential of kind `device`.
    token = models.ForeignKey(
        ApiToken,
        on_delete=models.CASCADE,
        related_name="devices",
    )
    # Server records the flag; the biometric gate itself is client-side (M5).
    biometric_bound = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def is_active(self) -> bool:
        """Not revoked — the lost-phone control (Section 12.1, ADR-006).

        Checked on every device-token authentication (fail closed alongside
        the token row's own validity) so a device revoked through any path
        stops working on the very next request.
        """
        return self.revoked_at is None

    def __str__(self) -> str:
        """Identify the row without formatting the sensitive push token."""
        return f"device:{self.pk}:{self.platform}"
