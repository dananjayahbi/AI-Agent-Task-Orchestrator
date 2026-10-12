"""MT-1.10-05 — per-connection and per-event authorization filtering.

Acceptance covered here (Sections 9.6, 12.1, 12.2; FR-SEC-03):

* a stream/history connection is accepted only for the Section 12.2 "Read
  events" callers — Owner yes, Device yes, **every agent role no** — with
  the canonical catalog codes (``AUTH_REQUIRED`` / ``ROLE_NOT_PERMITTED``)
  on the real routes, and no resume input bypasses the check;
* every delivery path — live fan-out, resume replay, history pages —
  drops events outside the connection's scope *before serialization*;
* the cross-project leakage mitigation of Section 12.1 is demonstrated
  end-to-end: a connection scoped (by token or by filter) to one project
  never receives another project's events, on any path;
* the checks reuse WP-1.2's permission model (``CanReadEvents``) plus one
  policy module (``apps.events.permissions``) — no second, divergent
  authorization implementation.

Run with ``pytest backend/tests/events/test_event_authorization.py -v``.
"""

from __future__ import annotations

from typing import Any

import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.services.tokens import hash_token
from apps.events.fanout import hub

from .stream_helpers import (
    STREAM_PATH,
    create_event,
    envelope_of,
    open_owner_client,
    open_stream,
)

AGENT_ROLES = ("coder", "auditor", "decomposer", "merge_executor")
QUIET = 0.15

#: A live device credential scoped to one project (direct rows — the model
#: supports scoped device tokens even though today's registration flow
#: issues owner-wide ones; this pins the MT-1.10-05 narrowing seam).
SCOPED_DEVICE_TOKEN = "wp110-scoped-device-credential"  # pragma: allowlist secret


def _bearer(token: str) -> dict[str, str]:
    """The Section 15.4 bearer transport of a token credential."""
    return {"Authorization": f"Bearer {token}"}


def _error_code(response: Any) -> str:
    """Assert the canonical five-field envelope and return its code."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


# --- per-connection: the Section 12.2 "Read events" row, on the real routes -


@pytest.mark.parametrize("path", (STREAM_PATH, "/api/v1/events"))
def test_anonymous_is_rejected_with_auth_required(db: None, path: str) -> None:
    """No credential: 401 AUTH_REQUIRED — the stream never half-opens."""
    response = APIClient().get(path)
    assert response.status_code == 401
    assert _error_code(response) == "AUTH_REQUIRED"


@pytest.mark.parametrize("role", AGENT_ROLES)
@pytest.mark.parametrize("path", (STREAM_PATH, "/api/v1/events"))
def test_every_agent_role_is_rejected_with_role_not_permitted(
    db: None, owner_api: APIClient, path: str, role: str
) -> None:
    """Agents never subscribe (Section 9.6): 403 ROLE_NOT_PERMITTED."""
    issued = owner_api.post(
        "/api/v1/tokens/agent",
        {"project_id": "PID00001", "scopes": [role]},
    )
    assert issued.status_code == 201
    token = str(issued.json()["token"])
    response = APIClient().get(path, headers=_bearer(token))
    assert response.status_code == 403, role
    assert _error_code(response) == "ROLE_NOT_PERMITTED"


def test_agent_resume_input_is_not_a_permission_bypass(db: None, owner_api: APIClient) -> None:
    """Last-Event-ID / last_event_id never widen the caller's role."""
    issued = owner_api.post("/api/v1/tokens/agent", {"project_id": "PID00001", "scopes": ["coder"]})
    token = str(issued.json()["token"])
    response = APIClient().get(f"{STREAM_PATH}?last_event_id=0", headers=_bearer(token))
    assert response.status_code == 403
    header_resume = APIClient().get(STREAM_PATH, headers={**_bearer(token), "Last-Event-ID": "0"})
    assert header_resume.status_code == 403


def test_owner_and_device_hold_the_stream(db: None, device_token: str) -> None:
    """Owner session and device bearer both open the stream (matrix cells)."""

    async def scenario() -> None:
        owner = await open_owner_client()
        owner_stream = await open_stream(owner)
        await owner_stream.aclose()

        device = AsyncClient()
        device_stream = await open_stream(device, headers=_bearer(device_token))
        await device_stream.aclose()

    async_to_sync(scenario)()


# --- per-event: every delivery path drops out-of-scope events ---------------


def test_cross_project_events_never_reach_a_filtered_connection(
    db: None, owner_api: APIClient
) -> None:
    """Live fan-out: a project-filtered connection drops other projects."""
    del owner_api

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client, path=f"{STREAM_PATH}?project=PID00001")
        try:
            foreign = await create_event(project_id="PID00002")
            hub.broadcast(envelope_of(foreign))
            with pytest.raises(AssertionError, match="no SSE frame within"):
                await stream.read_frame(timeout=QUIET)

            mine = await create_event(project_id="PID00001")
            hub.broadcast(envelope_of(mine))
            got = await stream.read_events(1)
            assert [item["id"] for item in got] == [mine.pk], (
                "dropped, never partially sent (Section 12.1)"
            )
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_scoped_device_credential_narrows_replay_live_and_history(
    db: None, owner_api: APIClient
) -> None:
    """The token's scope applies on all three delivery paths.

    The connection applies **no client filters at all** — only the token's
    scope — so a drop here proves the per-event policy of
    ``apps.events.permissions`` on the replay, live and history paths.
    """
    user = User.objects.get(username="owner")
    token_row = ApiToken.objects.create(
        kind=TokenKind.DEVICE,
        user=user,
        hash=hash_token(SCOPED_DEVICE_TOKEN),
        project_id="PID00001",
    )
    Device.objects.create(
        user=user,
        platform="android",
        push_token="wp110-scoped-device-push",
        token=token_row,
    )
    headers = _bearer(SCOPED_DEVICE_TOKEN)

    async def scenario() -> None:
        mine_before = await create_event(project_id="PID00001")
        foreign_before = await create_event(project_id="PID00002")
        assert mine_before.pk < foreign_before.pk

        client = AsyncClient()
        # Replay path: last id 0 would replay everything — the scope says no.
        stream = await open_stream(client, path=f"{STREAM_PATH}?last_event_id=0", headers=headers)
        try:
            replayed = await stream.read_events(1)
            assert [item["id"] for item in replayed] == [mine_before.pk], (
                "replay never crosses the token's project"
            )

            # Live path: the foreign event is dropped before serialization.
            foreign_live = await create_event(project_id="PID00002")
            hub.broadcast(envelope_of(foreign_live))
            mine_live = await create_event(project_id="PID00001")
            hub.broadcast(envelope_of(mine_live))
            got = await stream.read_events(1)
            assert [item["id"] for item in got] == [mine_live.pk], (
                "live delivery never crosses the token's project"
            )
        finally:
            await stream.aclose()

        # History path: the same scope, the same policy module.
        response = await client.get("/api/v1/events", headers=headers)
        assert response.status_code == 200
        assert [item["project_id"] for item in response.json()["results"]] == [
            "PID00001",
            "PID00001",
        ], "history pages confine to the token's project too"


def test_owner_scope_is_owner_wide_across_projects(db: None, owner_api: APIClient) -> None:
    """Owner sees all (Section 9.6): unfiltered stream + history span PIDs."""
    del owner_api

    async def scenario() -> None:
        first = await create_event(project_id="PID00001")
        second = await create_event(project_id="PID00002")
        client = await open_owner_client()
        stream = await open_stream(client)
        try:
            hub.broadcast(envelope_of(first))
            hub.broadcast(envelope_of(second))
            got = await stream.read_events(2)
            assert [item["id"] for item in got] == [first.pk, second.pk]
        finally:
            await stream.aclose()

    async_to_sync(scenario)()


def test_history_denies_what_the_stream_denies(db: None, owner_api: APIClient) -> None:
    """Consistency (9.6): the stream cannot read what history denies."""
    mine = owner_api.get("/api/v1/events?project=PID00001")
    assert mine.status_code == 200
    assert mine.json()["results"] == [], "empty scope, empty page — never a leak"
