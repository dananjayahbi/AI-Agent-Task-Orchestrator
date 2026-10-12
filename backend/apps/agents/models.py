"""The Agent Session entity (parent plan Sections 7.2, 10.2; MT-1.6-09).

Exactly the Section 7.2 "Agent Session (new)" table:

* ``id`` — bridge-issued, unguessable, **opaque** (G-18: the bridge
  issues a unique session id; the backend binds leases to token +
  session id). Validated at the API boundary and by a database check
  constraint against the same pattern (Section 7.4 reading) — shape
  only, never parsed into meaning.
* ``project`` / ``project_id`` — one project per session; resolved from
  the presenting token at open (ADR-004: never from the body).
* ``token_id`` — the ``ApiToken`` pk the bridge presented (Section 7.2
  ``token_id``; stored as the id, never the secret).
* ``agent_label`` — G-18: self-declared, spoofable, a *label only*.
* ``client_name`` — the MCP client name/version, input to Section 10.4's
  capability lookup later (stored, not resolved, here).
* ``capability`` — Section 10.4's closed triple, default ``unknown``
  ("Default ``unknown``, treated as text-safe").
* ``transport`` — Section 10.2's two run modes.
* ``started_at`` / ``last_seen_at`` / ``ended_at`` — lifecycle stamps;
  ``ended_at`` set exactly once by ``POST /agent-sessions/{id}/end``.

Mutability: ``ended_at`` is the only field the end endpoint writes —
sessions are not audit rows (Section 12.5's append-only rule covers
Event/Transition rows).
"""

from __future__ import annotations

import re

from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.projects.models import Project

#: Bridge-issued session id: 8–128 chars of URL-safe machinery (G-18
#: fixes "unguessable"; the plan states no format, so this is the
#: documented shape validation of MT-1.6-09's risk note).
SESSION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$"
SESSION_ID_RE = re.compile(SESSION_ID_PATTERN)

validate_session_id = RegexValidator(
    regex=SESSION_ID_PATTERN,
    message="Session id must be 8-128 characters of [A-Za-z0-9._:-] starting alphanumeric.",
)


class SessionCapability(models.TextChoices):
    """Section 10.4's closed triple — the values the bridge may declare."""

    VISION = "vision", "vision"
    TEXT_ONLY = "text_only", "text_only"
    UNKNOWN = "unknown", "unknown"


class SessionTransport(models.TextChoices):
    """Section 10.2's two run modes (plus none other)."""

    STDIO = "stdio", "stdio"
    HTTP = "http", "http"


class AgentSession(models.Model):
    """One connected agent instance — Section 7.2, field for field."""

    id = models.CharField(
        primary_key=True,
        max_length=128,
        validators=[validate_session_id],
        help_text="Bridge-issued, unguessable, opaque (G-18; Section 7.2).",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="agent_sessions",
        help_text="Section 7.2 project_id — from the token, never the body (ADR-004).",
    )
    token_id = models.PositiveBigIntegerField(
        help_text="The ApiToken pk presented at open (Section 7.2 token_id; never the secret)."
    )
    agent_label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Self-declared label only — spoofable by design (G-18).",
    )
    client_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="MCP client name/version as declared by the bridge (Section 10.4 input).",
    )
    capability = models.CharField(
        max_length=16,
        choices=SessionCapability.choices,
        default=SessionCapability.UNKNOWN,
        help_text="Section 10.4 closed triple; default unknown (text-safe).",
    )
    transport = models.CharField(
        max_length=8,
        choices=SessionTransport.choices,
        help_text="Section 10.2 run mode the bridge connected with.",
    )
    started_at = models.DateTimeField(
        default=timezone.now,
        help_text="Server time the session opened (Section 7.2).",
    )
    last_seen_at = models.DateTimeField(
        default=timezone.now,
        help_text="Advanced by later session-scoped calls (Section 7.2); set to "
        "started_at at open — no heartbeat invented (OQ-04 stays closed).",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Server time the bridge ended the session (Section 9.2 end row).",
    )

    class Meta:
        """Section 7.4 reading: the id pattern is enforced in the database too."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(id__regex=SESSION_ID_PATTERN),
                name="agent_session_id_format",
            ),
            models.CheckConstraint(
                condition=models.Q(capability__in=SessionCapability.values),
                name="agent_session_capability_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(transport__in=SessionTransport.values),
                name="agent_session_transport_canonical",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "ended_at"], name="agentsession_proj_ended"),
        ]

    def __str__(self) -> str:
        """Identify the row by opaque id and project."""
        return f"{self.id} @{self.project_id}"
