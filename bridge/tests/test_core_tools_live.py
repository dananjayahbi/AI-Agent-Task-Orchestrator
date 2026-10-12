"""MT-2.4-07 — core-tool suite against the real claim service (NFR-01; §18).

The honest concurrency half of WP-2.4's acceptance, driven **through the
bridge tools** at the HTTP boundary of a real running backend (spawned by
``_live_backend`` against ``wp16-pg``): two independent bridge sessions
claiming one task produce exactly one winner, and 50 parallel attempts yield
one winner with structured failures — never two winners, never a silent
error (``test_core_tools.py`` pins the bridge side with the send-seam fake;
this module pins the loop).

Gated: opt in with ``ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`` and
``docker start wp16-pg`` (port 5434); skipped otherwise with that command in
the reason — the unit battery stays green without the stack (documented in
the WP changelog). Each test owns one seeded task and releases its winner's
lease on the way out.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import threading
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.config import load_settings
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.errors import SessionOpenError
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.server import create_server
from orchestrator_bridge.session import (
    CAPABILITY_UNKNOWN,
    CLIENT_NAME,
    AgentSession,
    ProjectContext,
    new_session_id,
    open_session,
)
from orchestrator_bridge.tools.available_tasks import list_available_tasks
from orchestrator_bridge.tools.claim import claim_task
from orchestrator_bridge.tools.context import get_project_context
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.release import release_task
from orchestrator_bridge.tools.runtime import ToolRuntime
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES
from orchestrator_bridge.tools.task_details import get_task_details
from orchestrator_bridge.transport import ApiClient
from tests import _live_backend

_ABSENT_CONFIG = Path("no-such-bridge-config.toml")

#: The recorded backend gate (WP changelog follow-up): agent read-only access
#: to ``GET /projects/{pid}`` / ``GET /tasks/{id}`` is documented to activate
#: in a backend WP-2.x task and answers ROLE_NOT_PERMITTED until then.
_GATE_REASON = (
    "backend gate (recorded follow-up): agent read-only access to "
    "GET /projects/{pid} and GET /tasks/{id} is not active on this backend "
    "yet (ROLE_NOT_PERMITTED); re-run when the WP-2.x activation lands"
)

#: The two structured failure codes the claim algorithm may answer losers
#: with (Section 9.3 re-validation inside the lock; MT-2.4-07 acceptance).
_LOSER_CODES = {ErrorCode.TASK_ALREADY_CLAIMED, ErrorCode.CONCURRENCY_LIMIT_REACHED}

pytestmark = pytest.mark.skipif(
    _live_backend.skip_reason() is not None,
    reason=_live_backend.skip_reason() or "unreachable",
)


@pytest.fixture(scope="module")
def live_backend() -> Iterator[_live_backend.LiveBackend]:
    """One migrated, seeded backend for the module; torn down afterwards."""
    backend = _live_backend.start_live_backend()
    try:
        yield backend
    finally:
        _live_backend.stop_live_backend(backend)


def _manifest(live: _live_backend.LiveBackend) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project_id": live.project_id,
        "project_name": "Bridge IT Project",
        "orchestrator_api": live.api_base_url,
        "default_branch": "main",
        "auto_branch_prefix": f"feat/{live.project_id}-",
        "audit_required_default": True,
    }


def _bound(live: _live_backend.LiveBackend, token: str, *, allow_gate: bool = False) -> ToolRuntime:
    """A full bridge startup against the live backend: bind → open → context.

    ``allow_gate`` tolerates the *recorded backend gate* (follow-up in the WP
    changelog): agent read-only access to ``GET /projects/{pid}`` (and the
    task read) is documented to activate in a backend WP-2.x task and answers
    ``ROLE_NOT_PERMITTED`` until then — the session open itself succeeds, so
    the claim/release concurrency proofs stay honest without mocking.
    """
    settings = dataclasses.replace(
        load_settings(env={"ORCHESTRATOR_AGENT_TOKEN": token}, config_path=_ABSENT_CONFIG),
        timeout_seconds=30.0,
        retry_max_attempts=3,
    )
    binding = StartupBinding(manifest_path=Path("orchestrator.json"), manifest=_manifest(live))
    client = ApiClient.for_binding(binding, settings)
    try:
        session = open_session(binding, settings, client=client)
    except SessionOpenError as exc:
        if allow_gate and "ROLE_NOT_PERMITTED" in str(exc):
            session = _session_opening_only(client, binding)
        else:
            raise
    return ToolRuntime.from_session(binding, client, session)


def _session_opening_only(client: ApiClient, binding: StartupBinding) -> AgentSession:
    """Open just the backend session (no context reads) — the gate fallback.

    Mirrors MT-2.2-04's open exactly; only the step-5 context fetch is skipped
    (it is the denied call), and the cache holds a clearly-marked placeholder
    so no test can mistake it for backend data.
    """
    session_id = new_session_id()
    response = client.request(
        "POST",
        endpoint("session_open").path,
        body={
            "id": session_id,
            "client_name": CLIENT_NAME,
            "capability": CAPABILITY_UNKNOWN,
            "transport": "stdio",
        },
    )
    agent_session_id = (
        str(response.get("id"))
        if isinstance(response, Mapping) and isinstance(response.get("id"), str)
        else session_id
    )
    return AgentSession(
        agent_session_id=agent_session_id,
        context=ProjectContext(
            project_id=binding.project_id,
            name="(backend gate: agent project read pending)",
            rules="",
            policy_summary={},
        ),
    )


def test_advertises_the_core_tools_over_the_live_stack(
    live_backend: _live_backend.LiveBackend,
) -> None:
    """Sanity: a runtime bound to the live backend lists the five tools."""
    runtime = _bound(live_backend, live_backend.tokens[0], allow_gate=True)
    server = create_server(runtime.client._settings, runtime=runtime)  # noqa: SLF001
    tools = asyncio.run(server.list_tools())
    assert [tool.name for tool in tools] == list(CORE_TOOL_NAMES)


def test_orient_list_details_claim_release_chain(live_backend: _live_backend.LiveBackend) -> None:
    """The MT chain end-to-end: context → work list → details → claim → release.

    Exercises the real session open + project-context cache (MT-2.2-04), the
    agent-facing work read, the task read, the Section 9.3 claim and the
    fenced release — all through the bridge handlers, no backend test client.
    """
    task_id = live_backend.tasks[0]
    try:
        runtime = _bound(live_backend, live_backend.tokens[0])
    except SessionOpenError as exc:
        if "ROLE_NOT_PERMITTED" in str(exc):
            pytest.skip(_GATE_REASON)
        raise

    orient = get_project_context(runtime)
    assert orient["project_id"] == live_backend.project_id
    assert orient["project_name"] == "Bridge IT Project"
    assert orient["policy_summary"]["max_concurrent_tasks"] >= 1

    listing = list_available_tasks(runtime)
    assert task_id in {task["id"] for task in listing["tasks"]}

    details = get_task_details(runtime, task_id=task_id)
    assert details["task"]["id"] == task_id
    assert details["task"]["state"] == "pending"

    claimed = claim_task(runtime, task_id=task_id, agent_identifier="bridge-it-coder")
    assert claimed["branch"] == f"feat/{live_backend.project_id}-{task_id.split('-')[-1]}"
    assert claimed["lease"]["generation"] >= 1
    assert claimed["rules"]["standard_rules"]  # the backend's Section 10.6 block

    released = release_task(runtime, task_id=task_id, reason="chain complete")
    assert released["state"] == "pending"
    assert released["released"] is True


def test_two_bridges_one_task_produce_exactly_one_winner(
    live_backend: _live_backend.LiveBackend,
) -> None:
    """WP-2.4 acceptance: two independent bridge sessions (separate tokens)
    claim one task concurrently — one success, one TASK_ALREADY_CLAIMED with
    hint and next action (FR-LEA-01)."""
    task_id = live_backend.tasks[1]
    runtimes = [_bound(live_backend, token, allow_gate=True) for token in live_backend.tokens[:2]]
    barrier = threading.Barrier(len(runtimes))
    outcomes: list[tuple[int, str]] = []
    lock = threading.Lock()

    def attempt(index: int) -> None:
        runtime = runtimes[index]
        barrier.wait(timeout=30)
        try:
            claim_task(runtime, task_id=task_id, agent_identifier="bridge-it-racer")
            outcome = "claimed"
        except ToolFailure as exc:
            outcome = str(exc.translated.code)
            assert exc.translated.hint and exc.translated.next_action
        with lock:
            outcomes.append((index, outcome))

    threads = [threading.Thread(target=attempt, args=(index,)) for index in range(len(runtimes))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)

    codes = [outcome for _index, outcome in outcomes]
    winners = [index for index, outcome in outcomes if outcome == "claimed"]
    assert len(winners) == 1, codes
    losers = [outcome for outcome in codes if outcome != "claimed"]
    assert losers and set(losers) <= _LOSER_CODES, codes
    release_task(runtimes[winners[0]], task_id=task_id, reason="live-suite cleanup")


def test_fifty_parallel_claims_yield_one_winner(live_backend: _live_backend.LiveBackend) -> None:
    """Section 18 concurrency layer: 50 parallel claims of one task through
    the MCP tool boundary — exactly one winner; every loser a structured,
    catalog-coded failure with guidance (no partial state, no crashes)."""
    task_id = live_backend.tasks[2]
    runtimes = [
        _bound(live_backend, live_backend.tokens[index % 3], allow_gate=True) for index in range(10)
    ]
    servers = [create_server(runtime.client._settings, runtime=runtime) for runtime in runtimes]  # noqa: SLF001
    barrier = threading.Barrier(50)
    outcomes: list[tuple[int, str]] = []
    lock = threading.Lock()

    def attempt(index: int) -> None:
        server = servers[index % len(servers)]
        barrier.wait(timeout=60)
        try:
            asyncio.run(
                server.call_tool(
                    "claim_task", {"task_id": task_id, "agent_identifier": f"worker-{index}"}
                )
            )
            outcome = "claimed"
        except ToolError as exc:
            payload = json.loads(str(exc).removeprefix("Error executing tool claim_task: "))
            outcome = str(payload["code"])
            assert payload["hint"] and payload["next_action"]
        with lock:
            outcomes.append((index, outcome))

    threads = [threading.Thread(target=attempt, args=(index,)) for index in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=240)

    codes = [outcome for _index, outcome in outcomes]
    winners = [index for index, outcome in outcomes if outcome == "claimed"]
    assert len(winners) == 1, sorted(set(codes))
    losers = [outcome for outcome in codes if outcome != "claimed"]
    assert len(losers) == 49
    assert set(losers) <= _LOSER_CODES, sorted(set(losers))
    winner_runtime = runtimes[winners[0] % len(runtimes)]
    release_task(winner_runtime, task_id=task_id, reason="live-suite cleanup")


def test_mcp_dispatch_errors_over_live_are_structured(
    live_backend: _live_backend.LiveBackend,
) -> None:
    """A duplicate claim through the MCP boundary surfaces the catalog code
    as the ToolError JSON payload (the model-facing contract)."""
    task_id = live_backend.tasks[0]
    holder = _bound(live_backend, live_backend.tokens[0], allow_gate=True)
    claim_task(holder, task_id=task_id, agent_identifier="bridge-it-holder")
    try:
        other = _bound(live_backend, live_backend.tokens[1], allow_gate=True)
        server = create_server(other.client._settings, runtime=other)  # noqa: SLF001
        with pytest.raises(ToolError) as excinfo:
            asyncio.run(
                server.call_tool("claim_task", {"task_id": task_id, "agent_identifier": "late"})
            )
        payload = json.loads(str(excinfo.value).removeprefix("Error executing tool claim_task: "))
        assert payload["code"] in {code.value for code in _LOSER_CODES}
        assert payload["hint"] and payload["next_action"]
    finally:
        release_task(holder, task_id=task_id, reason="live-suite cleanup")
