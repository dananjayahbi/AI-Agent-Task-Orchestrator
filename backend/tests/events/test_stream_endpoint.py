"""MT-1.10-01 — the authenticated SSE stream endpoint with filters + history.

Acceptance covered here (Sections 9.6, 9.2, 12.2):

* ``GET /events/stream`` and ``GET /events`` require authentication —
  anonymous callers receive the canonical ``AUTH_REQUIRED`` envelope;
* agent tokens are rejected on both — the Section 12.2 "Read events" row
  and Section 9.6's "agents never subscribe" (``ROLE_NOT_PERMITTED``);
  Owner session (cookie) and device bearer tokens are accepted;
* the ``project``/``task`` filters (Section 9.6 names, used on both
  endpoints per MT-1.10-01's risk note) reject malformed values with the
  canonical ``VALIDATION_ERROR`` envelope;
* history returns stored rows in ``id`` order under the pagination.md
  cursor contract, each item exactly the Section 9.6 envelope;
* the stream response is an async ASGI stream with the no-buffering
  headers whose status line arrives while the body is still untouched
  (early flush — the incremental proof over the wire arrives with the
  heartbeat reads of MT-1.10-04).

Run with ``pytest backend/tests/events/test_stream_endpoint.py -v``.
"""

from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from django.test import AsyncClient
from rest_framework.test import APIClient

from apps.core.errors import AUTH_REQUIRED, CANONICAL_ERROR_CODES, ROLE_NOT_PERMITTED

from .stream_helpers import (
    STREAM_PATH,
    envelope_of,
    make_event,
    open_owner_client,
    open_stream,
)


def _code(response: Any) -> str:
    """Assert the canonical five-field envelope and return its code."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    return str(error["code"])


# --- authentication (Section 12.2 "Read events" row) ------------------------


def test_both_endpoints_require_authentication(db: None) -> None:
    """Anonymous: 401 AUTH_REQUIRED on stream and history, JSON envelope."""
    client = APIClient()
    for path in (STREAM_PATH, "/api/v1/events"):
        response = client.get(path)
        assert response.status_code == 401, path
        assert _code(response) == AUTH_REQUIRED
        assert response["Content-Type"].startswith("application/json"), (
            "a rejected stream answers the envelope, never a half-open stream"
        )


def test_agents_never_subscribe(db: None, agent_token: str) -> None:
    """Agent bearer: 403 ROLE_NOT_PERMITTED on stream and history (9.6)."""
    client = APIClient()
    headers = {"Authorization": f"Bearer {agent_token}"}
    for path in (STREAM_PATH, "/api/v1/events"):
        response = client.get(path, headers=headers)
        assert response.status_code == 403, path
        assert _code(response) == ROLE_NOT_PERMITTED


def test_owner_session_opens_the_stream(db: None, owner_api: APIClient) -> None:
    """Owner cookie transport: the stream opens and can be closed cleanly."""
    del owner_api  # creates the owner user; the async client logs in itself

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        assert stream.response.status_code == 200
        assert stream.response.streaming is True
        await stream.aclose()

    async_to_sync(scenario)()


def test_device_token_opens_the_stream(db: None, device_token: str) -> None:
    """Device bearer (Section 15.4 transport): a valid stream caller."""
    headers = {"Authorization": f"Bearer {device_token}"}

    async def scenario() -> None:
        client = AsyncClient()
        stream = await open_stream(client, headers=headers)
        assert stream.response.status_code == 200
        assert stream.response.streaming is True
        await stream.aclose()

    async_to_sync(scenario)()


# --- filters (Section 9.6 names, validated to the canonical envelope) -------


def test_malformed_filters_answer_validation_error(db: None, owner_api: APIClient) -> None:
    """Bad `project`/`task` values: 400 VALIDATION_ERROR before any stream."""
    for path in (
        f"{STREAM_PATH}?project=NOTAPID",
        f"{STREAM_PATH}?task=oops",
        "/api/v1/events?project=NOTAPID",
        "/api/v1/events?task=oops",
    ):
        response = owner_api.get(path)
        assert response.status_code == 400, path
        assert _code(response) == "VALIDATION_ERROR", path


def test_history_filters_narrow_to_the_requested_project(db: None, owner_api: APIClient) -> None:
    """`project` and `task` filters select exactly the matching rows."""
    p1 = make_event(project_id="PID00001", task_id="PID00001-T001")
    p1_other = make_event(project_id="PID00001")
    make_event(project_id="PID00002")

    by_project = owner_api.get("/api/v1/events?project=PID00001")
    assert by_project.status_code == 200
    ids = [item["id"] for item in by_project.json()["results"]]
    assert ids == [p1.pk, p1_other.pk]

    by_task = owner_api.get("/api/v1/events?task=PID00001-T001")
    assert by_task.status_code == 200
    assert [item["id"] for item in by_task.json()["results"]] == [p1.pk]


# --- history ordering + envelope (Sections 9.6, 20.5; pagination.md) --------


def test_history_returns_the_seven_key_envelope_in_id_order(db: None, owner_api: APIClient) -> None:
    """Rows page oldest → newest by id; each item is the Section 9.6 shape."""
    first = make_event(type="project.created")
    second = make_event(type="task.created", task_id="PID00001-T001")
    third = make_event(type="task.updated", task_id="PID00001-T001")

    response = owner_api.get("/api/v1/events")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"results", "next_cursor"}, "pagination.md envelope"
    assert body["next_cursor"] is None
    assert [item["id"] for item in body["results"]] == [first.pk, second.pk, third.pk]
    for item in body["results"]:
        assert set(item) == {
            "id",
            "type",
            "project_id",
            "task_id",
            "occurred_at",
            "actor",
            "data",
        }, "Section 9.6 envelope keys, unchanged"
        assert set(item["actor"]) == {"type", "ref"}


def test_history_paginates_with_the_canonical_cursor(db: None, owner_api: APIClient) -> None:
    """cursor/page_size contract: pages stitch to the id-ordered whole."""
    rows = [make_event() for _ in range(3)]

    first_page = owner_api.get("/api/v1/events?page_size=2")
    assert first_page.status_code == 200
    body = first_page.json()
    assert [item["id"] for item in body["results"]] == [rows[0].pk, rows[1].pk]
    assert body["next_cursor"] is not None

    second_page = owner_api.get("/api/v1/events", {"page_size": 2, "cursor": body["next_cursor"]})
    assert second_page.status_code == 200
    page_two = second_page.json()
    assert [item["id"] for item in page_two["results"]] == [rows[2].pk]
    assert page_two["next_cursor"] is None

    bad_cursor = owner_api.get("/api/v1/events?cursor=not-opaque")
    assert bad_cursor.status_code == 400
    assert _code(bad_cursor) == "VALIDATION_ERROR"


# --- streaming response shape (early flush; no-buffering headers) -----------


def test_stream_response_is_an_unbuffered_asgi_stream(db: None, owner_api: APIClient) -> None:
    """Status + headers flush while the body is untouched (early flush).

    The response is an *async* iterator, which Django's ASGI handler streams
    incrementally; a sync iterator would be materialized through
    ``sync_to_async(list)`` — whole-body buffering, the failure mode the
    no-buffering headers exist to prevent. The heartbeat reads of
    MT-1.10-04 prove first-byte arrival over the wire; this asserts the
    structural half plus the headers the edge needs (RISK-05).
    """
    del owner_api  # creates the owner user; the async client logs in itself

    async def scenario() -> None:
        client = await open_owner_client()
        stream = await open_stream(client)
        response = stream.response
        assert response.status_code == 200
        assert response.streaming is True
        assert response.is_async is True, "async generator = incremental ASGI path"
        assert response["Content-Type"].startswith("text/event-stream")
        assert response["Cache-Control"] == "no-cache"
        assert response["X-Accel-Buffering"] == "no"
        # The body has not been read — the response start arrived first.
        await stream.aclose()

    async_to_sync(scenario)()


def test_history_envelope_equals_the_stored_projection(db: None) -> None:
    """History items are byte-for-byte the `event_envelope` projection."""
    event = make_event(type="task.transitioned", task_id="PID00001-T007")
    assert set(envelope_of(event)) == {
        "id",
        "type",
        "project_id",
        "task_id",
        "occurred_at",
        "actor",
        "data",
    }
