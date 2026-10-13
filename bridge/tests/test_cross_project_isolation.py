"""MT-2.9-04 — the two-connections cross-project isolation test (Sections 10.2,
10.3, 18; FR-MCP-06, FR-MCP-01, NFR-04).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.9-http-transport/
MT-2.9-04-isolation-test.md. WP-2.9's acceptance in one file: **two
simultaneous connections for different projects never share state.**

The traffic is genuinely concurrent — two client threads meet on a barrier
and then drive their own connection through interleaved tool calls (no
sleep-ordering) — against the real multi-connection server over real
sockets. Every observable is asserted on its own side of the boundary:
context, listings, claim visibility, session identity, then the deliberate
cross-project attempts (rejected locally, catalog code) and the teardown
check (closing A leaves B fully functional).
"""

from __future__ import annotations

import threading
from typing import Any

from tests.http_harness import (
    happy_backend,
    http_settings,
    running_bridge,
    service_envelope,
    wait_for,
)

_PID_A = "PID00007"
_PID_B = "PID00008"
_TASK_A = "PID00007-T004"
_TASK_B = "PID00008-T001"


def _task_row(task_id: str, title: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": title,
        "priority": "high",
        "state": "pending",
        "depends_on": [],
    }


def _claim_body(task_id: str, session_id: str) -> dict[str, Any]:
    return {
        "task": {
            "id": task_id,
            "title": "Ship the kettle UI",
            "state": "in_progress",
            "test_command": "pytest -q",
        },
        "lease": {
            "assigned_agent": "coder-a",
            "session_id": session_id,
            "role": "coder",
            "lease_generation": 7,
            "lease_acquired_at": "2026-10-13T10:00:00Z",
            "lease_expires_at": "2026-10-13T10:45:00Z",
            "lease_hard_cap_at": "2026-10-13T12:00:00Z",
            "last_checkpoint": None,
            "failure_retry_count": 0,
        },
        "rules_block": {"text": "backend rules block (wire copy)"},
    }


def test_cross_project_isolation_two_simultaneous_connections() -> None:
    """The WP acceptance: interleaved traffic, zero state crossover."""
    fake = happy_backend((_PID_A, "Tea Factory ERP"), (_PID_B, "Second Project"))
    # Project A's listing updates after its claim (backend-style); project B's
    # own fixture is untouched by anything A does.
    claimed = {"flag": False}
    fake.route_fn(
        "GET",
        f"/api/v1/projects/{_PID_A}/work",
        lambda _body: (
            200,
            {
                "results": [] if claimed["flag"] else [_task_row(_TASK_A, "Kettle UI")],
                "next_cursor": None,
            },
        ),
    )
    fake.route(
        "GET",
        f"/api/v1/projects/{_PID_B}/work",
        200,
        {"results": [_task_row(_TASK_B, "Warehouse sync")], "next_cursor": None},
    )
    fake.route_fn(
        "POST",
        f"/api/v1/tasks/{_TASK_A}/claim",
        lambda body: (
            claimed.update(flag=True) or 200,
            _claim_body(_TASK_A, str(body["session_id"])),
        ),
    )

    with running_bridge(http_settings(), send=fake.send) as bridge:
        client_a = bridge.client(_PID_A, "token-for-A")
        client_b = bridge.client(_PID_B, "token-for-B")
        client_a.connect()
        client_b.connect()

        barrier = threading.Barrier(2, timeout=15)
        results: dict[str, Any] = {}
        errors: list[BaseException] = []

        def _drive_a() -> None:
            try:
                barrier.wait()
                results["ctx_a"] = client_a.call_payload("get_project_context")
                results["list_a1"] = client_a.call_payload("get_available_tasks", {"limit": 10})
                results["claim_a"] = client_a.call_payload(
                    "claim_task",
                    {"task_id": _TASK_A, "agent_identifier": "coder-a"},
                )
                results["list_a2"] = client_a.call_payload("get_available_tasks", {"limit": 10})
            except BaseException as exc:  # surfaced to the main thread below
                errors.append(exc)

        def _drive_b() -> None:
            try:
                barrier.wait()
                results["ctx_b"] = client_b.call_payload("get_project_context")
                results["list_b1"] = client_b.call_payload("get_available_tasks", {"limit": 10})
                results["list_b2"] = client_b.call_payload("get_available_tasks", {"limit": 10})
            except BaseException as exc:
                errors.append(exc)

        thread_a = threading.Thread(target=_drive_a, name="conn-a")
        thread_b = threading.Thread(target=_drive_b, name="conn-b")
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=20)
        thread_b.join(timeout=20)
        assert not thread_a.is_alive() and not thread_b.is_alive(), "traffic hung"
        assert not errors, errors

        # --- context stays on its own side -----------------------------------
        assert results["ctx_a"]["project_id"] == _PID_A
        assert results["ctx_a"]["project_name"] == "Tea Factory ERP"
        assert "Rules for Tea Factory ERP." in results["ctx_a"]["rules"]
        assert results["ctx_b"]["project_id"] == _PID_B
        assert results["ctx_b"]["project_name"] == "Second Project"
        assert "Rules for Second Project." in results["ctx_b"]["rules"]

        # --- listings never cross --------------------------------------------
        assert [t["id"] for t in results["list_a1"]["tasks"]] == [_TASK_A]
        assert [t["id"] for t in results["list_b1"]["tasks"]] == [_TASK_B]
        assert [t["id"] for t in results["list_b2"]["tasks"]] == [_TASK_B]

        # --- A's claim is invisible to B, and reshapes only A's listing ------
        assert results["claim_a"]["branch"] == f"feat/{_PID_A}-T004"  # G-09 default
        assert results["claim_a"]["task_id"] == _TASK_A
        assert results["list_a2"]["tasks"] == []
        assert [t["id"] for t in results["list_b2"]["tasks"]] == [_TASK_B]

        # --- session identity: two distinct backend sessions ------------------
        opens = fake.calls_to("POST", "/api/v1/agent-sessions")
        assert len(opens) == 2
        minted = {call.body["id"] for call in opens}
        assert len(minted) == 2
        registry = bridge.server.config.app.registry
        conn_a = registry.get(str(client_a.session_id))
        conn_b = registry.get(str(client_b.session_id))
        assert conn_a is not None and conn_b is not None
        assert conn_a.session.agent_session_id != conn_b.session.agent_session_id

        # --- negative: cross-project attempts fail locally (FR-MCP-06) -------
        calls_before = len(fake.calls)
        cross = client_a.raw_post(
            {"jsonrpc": "2.0", "id": 91, "method": "tools/list", "params": {}},
            project_id=_PID_B,
        )
        assert cross.status_code == 403
        cross_error = cross.json()["error"]
        assert cross_error["code"] == "AUTH_FORBIDDEN_PROJECT"
        assert cross_error["details"]["reason"] == "cross_project_request"

        smuggled = client_a.call_error_payload(
            "get_available_tasks", {"limit": 5, "project_id": _PID_B}
        )
        assert smuggled["code"] == "VALIDATION_ERROR"
        assert len(fake.calls) == calls_before, (
            "a rejected cross-project attempt must produce no backend traffic"
        )

        # --- teardown: closing A leaves B fully functional --------------------
        assert client_a.delete_session() in (200, 202, 204)
        wait_for(
            lambda: registry.get(str(client_a.session_id)) is None,
            message="connection A finalized",
        )
        assert registry.get(str(client_b.session_id)) is not None
        ctx_b_again = client_b.call_payload("get_project_context")
        assert ctx_b_again["project_id"] == _PID_B
        assert [
            t["id"] for t in client_b.call_payload("get_available_tasks", {"limit": 10})["tasks"]
        ] == [_TASK_B]
        assert client_b.health().json()["connections"] == 1
        ends = [c for c in fake.calls if c.path.endswith("/end")]
        assert len(ends) == 1  # exactly A's session ended so far


def test_cross_project_isolation_backend_sessions_scoped_per_token() -> None:
    """A wrong-project token cannot even open B's context (second barrier)."""
    fake = happy_backend((_PID_A, "Tea"), (_PID_B, "Second"))
    fake.route(
        "GET",
        f"/api/v1/projects/{_PID_A}",
        403,
        service_envelope("AUTH_FORBIDDEN_PROJECT", "not your project"),
    )
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "token-actually-for-B")
        response = client.raw_post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "iso", "version": "1"},
                },
            }
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "AUTH_FORBIDDEN_PROJECT"
        assert client.health().json()["connections"] == 0
