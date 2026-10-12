"""The API Token entity (parent plan Section 7.2; MT-1.2-01, MT-1.2-02).

Section 7.2 fixes the field set: ``id``, ``kind`` (``owner_session`` /
``agent`` / ``device``), ``hash`` (never plaintext), ``project_id`` (required
for ``agent``), ``scopes``, ``expires_at``, ``revoked_at``, ``last_used_at`` —
all present after MT-1.2-02 completes the slice started in MT-1.2-01 (each
step with its own standalone migration, Section 20.3: never combine a
migration with unrelated logic).

Representation decisions (recorded in the WP changelog):

* ``project_id`` stores the canonical Section 7.3 project identifier string
  (``PID`` + five digits) rather than a foreign key — the Project registry
  arrives with WP-1.3 (scope guard: this work package never models projects),
  and the string is exactly what ADR-004's backend scope check compares
  against. Two database ``CheckConstraint``s make a malformed token row
  impossible: ``kind = agent`` requires a ``project_id``, and any stored
  ``project_id`` must match the PID format (Section 7.3: ids are validated at
  every API boundary *and* by a database check constraint).
* ``scopes`` is a JSON list of the Section 12.2 agent role names (``coder``,
  ``auditor``, ``decomposer``, ``merge_executor``) carried on ``agent`` tokens;
  role *evaluation* is MT-1.2-05's matrix work, not this model's.

Invariant of the whole entity (Section 7.2, FR-SEC-04): ``hash`` is the **only**
secret representation — no code path may store, log or return the plaintext
token. ``__str__`` therefore never includes the hash (any path that formats the
model for a log line would otherwise leak every token).
"""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Section 7.3 project identifier: PID plus exactly five digits. Canonical
# home: ``apps.projects.services.pids`` (Section 9.1 — the ``projects``
# module owns ids; MT-1.3-01). Re-exported here so WP-1.2's public names —
# and every migration/serializer importing them — keep working unchanged;
# one pattern definition, no drift. Listed in ``__all__`` below as an
# explicit re-export (mypy strict).
from apps.projects.services.pids import PROJECT_ID_PATTERN, validate_project_id

# Section 12.2 agent roles carried in an agent token's `scopes` (MT-1.2-05's
# reading of the matrix, recorded in MT-1.2-02's changelog: roles ride on
# scopes; the `kind` enum stays closed at three). Issuance validates against
# this vocabulary; permission classes evaluate it.
AGENT_ROLE_SCOPES: tuple[str, ...] = ("coder", "auditor", "decomposer", "merge_executor")


class TokenKind(models.TextChoices):
    """The closed Section 7.2 kind enum — three values, none added."""

    OWNER_SESSION = "owner_session", "owner session"
    AGENT = "agent", "agent"
    DEVICE = "device", "device"


class ApiToken(models.Model):
    """One revocable, expiring credential; plaintext exists only in transit."""

    kind = models.CharField(max_length=16, choices=TokenKind.choices)
    # SHA-256 hex (64 chars) of the plaintext token — the fast lookup hash for
    # high-entropy bearer material (algorithm choice recorded in the WP
    # changelog; unsalted fast hashing is correct here precisely because the
    # input is 256-bit random, unlike passwords). Unique: it doubles as the
    # lookup index authentication performs on every request.
    hash = models.CharField(max_length=64, unique=True)
    # Section 7.1: API Token N:1 User — a token belongs to the owner account
    # that holds (session), creates (agent) or is bound to (device) it.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    # Section 7.2: required for kind=agent (ADR-004), nullable otherwise —
    # owner sessions and devices are not project-bound.
    project_id = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        validators=[validate_project_id],
        help_text="Canonical project id (PID + five digits); required for agent tokens.",
    )
    # Section 7.2 `scopes`: role names carried by agent tokens (Section 12.2
    # roles ride on scopes per MT-1.2-05's reading — kinds stay closed at
    # three). Empty list means "no explicit roles" (evaluation deferred).
    scopes = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        """Section 7.2/ADR-004 invariants enforced by the database itself."""

        constraints = [
            # django-stubs still spells this kwarg `condition`; Django 5.1+
            # renamed it to `check` (both accepted at runtime, 5.2 signature).
            models.CheckConstraint(  # type: ignore[call-arg]
                check=~models.Q(kind=TokenKind.AGENT) | models.Q(project_id__isnull=False),
                name="apitoken_agent_requires_project",
            ),
            models.CheckConstraint(  # type: ignore[call-arg]
                check=models.Q(project_id__isnull=True)
                | models.Q(project_id__regex=PROJECT_ID_PATTERN),
                name="apitoken_project_id_format",
            ),
        ]

    def clean(self) -> None:
        """Model-level mirror of the agent-requires-project constraint."""
        super().clean()
        if self.kind == TokenKind.AGENT and not self.project_id:
            raise ValidationError({"project_id": "Agent tokens require a project_id (ADR-004)."})

    def is_valid(self, at: datetime | None = None) -> bool:
        """The Section 7.2 / FR-SEC-02 validity half: not revoked, not expired.

        Evaluated **per request against the row** (no caching), so revocation
        takes effect on the very next call (WP-1.2 acceptance: "revoked tokens
        fail immediately"). The project half of the canonical predicate is
        ``matches_project``; ``is_usable_for`` combines both.
        """
        now = at or timezone.now()
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return True

    def matches_project(self, project_id: str | None) -> bool:
        """The ADR-004 project half: agent tokens address exactly one project.

        Only ``kind = agent`` tokens are project-bound (Section 7.2 requires
        ``project_id`` for agent — the other kinds are inherently unbound: an
        owner session may address any project, a device belongs to a user).
        An agent row without a project cannot match anything (the DB
        constraint prevents one existing; this fails closed regardless).
        """
        if self.kind != TokenKind.AGENT:
            return True
        return self.project_id is not None and self.project_id == project_id

    def is_usable_for(self, project_id: str | None = None, at: datetime | None = None) -> bool:
        """The canonical predicate: live **and** in-scope for *project_id*.

        Single source for authentication checks (MT-1.2-03 bearer auth and
        MT-1.2-05's project guard call this; ADR-004: the backend — not the
        bridge — is the authority for scope).
        """
        return self.is_valid(at) and self.matches_project(project_id)

    def __str__(self) -> str:
        """Identify the row without ever formatting the secret hash."""
        return f"{self.kind}:{self.pk}"


# Explicit exports (mypy strict): includes the Section 7.3 pattern and
# validator re-exported from their canonical home in apps.projects (9.1).
__all__ = [
    "AGENT_ROLE_SCOPES",
    "PROJECT_ID_PATTERN",
    "ApiToken",
    "TokenKind",
    "validate_project_id",
]
