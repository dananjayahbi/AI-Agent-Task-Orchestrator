"""Agent session open/end services (Section 9.2 Sessions row; MT-1.6-09).

Two operations, one small module:

* :func:`open_session` — creates the Section 7.2 row with
  ``project_id``/``token_id`` supplied by the *authenticated* caller
  (ADR-004 — the service never accepts a project from a payload).
  ``started_at`` and ``last_seen_at`` are stamped to the same ``now`` so
  a fresh session reads coherently; no heartbeat advances
  ``last_seen_at`` until a later WP defines one (OQ-04 stays closed).
  A duplicate id answers ``VALIDATION_ERROR``: the closed catalog has no
  id-collision code (Section 20.4 item 5) and retries are the
  ``Idempotency-Key`` replay's job, not a second row's.
* :func:`end_session` — sets ``ended_at`` exactly once under a row lock;
  a repeat call (the bridge's best-effort shutdown may run twice) returns
  the stored row without a second write. Unknown id answers DRF's
  ``NotFound``, which the core handler deliberately maps to ``400
  VALIDATION_ERROR`` for resources with no catalog code of their own
  (the projects reading, ``apps/core/exceptions.py``).
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.exceptions import AuthForbiddenProject

from .models import AgentSession


def open_session(
    *,
    session_id: str,
    project_id: str,
    token_id: int,
    agent_label: str,
    client_name: str,
    capability: str,
    transport: str,
) -> AgentSession:
    """Create one session row; the project comes from the token (ADR-004)."""
    if AgentSession.objects.filter(pk=session_id).exists():
        raise ValidationError({"id": "A session with this id already exists."})
    now = timezone.now()
    try:
        return AgentSession.objects.create(
            id=session_id,
            project_id=project_id,
            token_id=token_id,
            agent_label=agent_label,
            client_name=client_name,
            capability=capability,
            transport=transport,
            started_at=now,
            last_seen_at=now,
            ended_at=None,
        )
    except IntegrityError:
        # Two identical opens raced the primary key: same refusal, no 500.
        raise ValidationError({"id": "A session with this id already exists."}) from None


def end_session(*, session_id: str, project_id: str) -> AgentSession:
    """Set ``ended_at`` once (idempotent replay for a second call)."""
    with transaction.atomic():
        session = AgentSession.objects.select_for_update().filter(pk=session_id).first()
        if session is None:
            raise NotFound(f"Agent session {session_id} does not exist.")
        if session.project_id != project_id:
            # Defense in depth beside HasSessionProjectScope (ADR-004):
            # the service itself never trusts the route alone.
            raise AuthForbiddenProject(
                f"Token is scoped to {project_id!r}, not {session.project_id!r}."
            )
        if session.ended_at is None:
            session.ended_at = timezone.now()
            session.save(update_fields=["ended_at"])
        return session
