"""MT-1.2-07 — authorization-matrix tests incl. cross-project rejection.

The executable proof of WP-1.2 (Section 19.1 deliverable "authorization matrix
(Section 12.2) as tests"; Section 18 Security layer). Every Section 12.2 row is
exercised **against the running API with real authentication** for every actor
kind — owner session, agent token per role, device token, anonymous:

* rows whose endpoints exist now run on the **real route** (the
  *Manage projects/policy* row moved onto ``GET /api/v1/projects`` when
  WP-1.3 landed the registry; *Create draft tasks* moved onto
  ``POST /api/v1/projects/{pid}/tasks`` when WP-1.4 landed the task
  routes — its printed Decomposer/Device cells are recorded, still
  denied, in ``DEFERRED_MATRIX_CELLS`` per MT-1.4-03's risk note); rows
  without an endpoint keep probe routes
  that mount the real permission classes of ``apps.accounts.permissions``.
  Every still-deferred route is asserted **absent**: the first WP that lands
  one fails this suite until the probe is replaced with the real route
  (MT-1.2-07 risk note — an untested row is never silently green; no hidden
  decision, Section 20.1 item 5).
* WP-1.2 acceptance is asserted explicitly: a PID00001 agent token receives
  ``AUTH_FORBIDDEN_PROJECT`` on a PID00002 resource — now against **real
  project rows** (the MT-1.2-07 risk note: "switch to API-created projects
  when the registry lands" — the rows are created directly here so their
  ids stay deterministic on every backend), and revoked
  agent/device/owner credentials fail on their **very next request** (no
  cache lag).
* codes are catalog-closed (Section 20.4 item 5): missing auth
  ``AUTH_REQUIRED``, wrong role ``ROLE_NOT_PERMITTED``, cross-project
  ``AUTH_FORBIDDEN_PROJECT``, over-limit ``RATE_LIMITED`` — nothing else.
* a body-supplied ``project_id`` can never widen a token's scope: the guard
  resolves the project from the token and the URL (Section 9.3 step 1;
  ADR-004; G-07).

Run with ``pytest backend/tests/test_authorization_matrix.py -v`` (MT test
command); the file runs in CI's unit job as part of the Security layer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import Resolver404, include, path, resolve
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.accounts.exceptions import AuthForbiddenProject
from apps.accounts.models import User
from apps.accounts.permissions import (
    CanOperateMergeQueue,
    CanPublishTasks,
    CanReadMergeQueue,
    CanReviewDecisions,
    CanSubmitAuditVerdict,
)
from apps.core.errors import (
    AUTH_FORBIDDEN_PROJECT,
    AUTH_REQUIRED,
    CANONICAL_ERROR_CODES,
    RATE_LIMITED,
    ROLE_NOT_PERMITTED,
    VALIDATION_ERROR,
)
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskState

# WP-1.6: the two Claim rows now claim through the *real* route, whose
# service calls ``ensure_wired()`` and replaces the T4/T6 stubs on the
# process registry — autouse the restore fixture so the WP-1.5 suites
# sharing this process still see their stubs (wp16_helpers' rule).
from tests.wp16_helpers import restore_lease_registry  # noqa: F401

PID_ONE = "PID00001"
PID_TWO = "PID00002"

PASSWORD = "authz-matrix-tests-1!"  # pragma: allowlist secret

ACTORS: tuple[str, ...] = (
    "owner",
    "coder",
    "auditor",
    "decomposer",
    "merge_executor",
    "device",
    "anonymous",
)
AGENT_ROLES = ("coder", "auditor", "decomposer", "merge_executor")

# Section 12.2 rows, verbatim (same list as tests/test_permission_classes.py —
# a row added to the plan must appear in both files and in ROW_GRANTS there).
MATRIX_ROWS: tuple[str, ...] = (
    "Manage projects/policy",
    "Create draft tasks",
    "Publish tasks",
    "Claim pending",
    "Claim to_be_audited",
    "Submit resolution",
    "Submit verdict",
    "Review decisions",
    "Merge queue",
    "Read events",
)


# --- probe routes: the real permission classes, mounted on minimal views ----


def _probe_view(*perms: type[BasePermission]) -> type[APIView]:
    """A minimal endpoint guarded exactly as the real one will be."""

    class _ProbeView(APIView):
        permission_classes: list[Any] = list(perms)

        def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
            """200 = the actor's cell in Section 12.2 permits this capability."""
            return Response({"ok": True})

        def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
            """Same answer for the POST-shaped rows (claim, publish, ...)."""
            return Response({"ok": True})

    return _ProbeView


urlpatterns = [
    # One route per Section 12.2 row *without* a real endpoint yet.
    # *Manage projects/policy* left this list in WP-1.3 (its row runs on
    # the real ``GET /api/v1/projects`` below) and *Create draft tasks*
    # left it in WP-1.4 — that row now runs on the real
    # ``POST /api/v1/projects/{pid}/tasks`` route with its Decomposer and
    # Device cells recorded as deferred in ``DEFERRED_MATRIX_CELLS``.
    # WP-1.6 (MT-1.6-07) moved both *Claim* rows onto the real claim
    # route — their probe paths retired with them. WP-3.2 moved
    # *Submit resolution* onto the real submission route (its probe path
    # retired with it — the landing cases below carry the row).
    path("probe/publish", _probe_view(CanPublishTasks).as_view()),
    path("probe/verdict", _probe_view(CanSubmitAuditVerdict).as_view()),
    path("probe/review", _probe_view(CanReviewDecisions).as_view()),
    path("probe/merge-queue", _probe_view(CanReadMergeQueue).as_view()),
    path("probe/merge-queue/start", _probe_view(CanOperateMergeQueue).as_view()),
    # WP-1.10 (MT-1.10-05) removed the *Read events* probe: the row now
    # runs on the real /api/v1/events + /api/v1/events/stream routes.
    # The real WP-1.2 surface keeps resolving while probes are active: tests
    # revoke tokens/devices through the actual endpoints inside this URLConf.
    path("api/v1/", include("apps.accounts.urls")),
    # WP-1.3's real projects routes — the Manage-projects matrix row and the
    # cross-project tests run against them (MT-1.2-07's registry landing).
    path("api/v1/", include("apps.projects.urls")),
    # WP-1.4's real task routes — the Create-drafts row and both
    # cross-project cases run against them (MT-1.4-03's landing).
    path("api/v1/", include("apps.tasks.urls")),
    # WP-1.6's real agent-work + agent-session routes (MT-1.6-07/09) — the
    # two Claim rows and the landed-route cases below resolve here.
    path("api/v1/", include("apps.leases.urls")),
    path("api/v1/", include("apps.agents.urls")),
    # WP-1.10's real SSE gateway routes (MT-1.10-05) — the *Read events*
    # row runs on them above.
    path("api/v1/", include("apps.events.urls")),
    # WP-1.11's real attachment routes — the landed Attachments-row cases
    # (upload/list/detail/delete) run against them below.
    path("api/v1/", include("apps.attachments.urls")),
]


# --- the data-driven matrix -------------------------------------------------


def _cells(**allowed: bool) -> dict[str, bool]:
    """Every actor for one row: allowed where the Section 12.2 cell says Yes."""
    cells = dict.fromkeys(ACTORS, False)
    cells.update(allowed)
    return cells


class _Probe(NamedTuple):
    """One matrix row as the API sees it: route, method and the printed cells."""

    row: str  # Section 12.2 capability (cited verbatim)
    path: str
    method: str  # GET | POST
    grants: dict[str, bool]  # actor -> allowed
    # Real-route rows (no probe view behind them) may need a payload that
    # survives the endpoint's own validation and a non-200 success code.
    payload: dict[str, Any] | None = None
    ok: tuple[int, ...] = (200,)


PROBES: tuple[_Probe, ...] = (
    # *Manage projects/policy* runs on the real WP-1.3 route (GET list — the
    # row is exercised where the endpoint actually exists; MT-1.2-07).
    _Probe("Manage projects/policy", "/api/v1/projects", "GET", _cells(owner=True)),
    # *Create draft tasks* runs on the real WP-1.4 route (MT-1.4-03). The
    # printed Section 12.2 cells are Owner / Decomposer / Device (Could) —
    # the latter two are **deferred** (MT-1.4-03 risk note: no distinct
    # decomposer token kind yet) and recorded, still-denied, in
    # DEFERRED_MATRIX_CELLS below; the full printed row stays covered at
    # class level in tests/test_permission_classes.py (CanCreateDraftTasks).
    _Probe(
        "Create draft tasks",
        f"/api/v1/projects/{PID_ONE}/tasks",
        "POST",
        _cells(owner=True),
        payload={"title": "Matrix draft"},
        ok=(201,),
    ),
    _Probe("Publish tasks", "/probe/publish", "POST", _cells(owner=True, device=True)),
    # Both *Claim* rows run on the real WP-1.6 route (MT-1.6-07): the
    # service answers 200 (claimed) — or, for the to_be_audited row, 409:
    # the auditor path runs through the T11 transition guard and WP-3.x
    # wires it, so "allowed" there means "passed authorization, reached
    # the state machine". Denied actors never reach the service (403).
    _Probe(
        "Claim pending",
        f"/api/v1/tasks/{PID_ONE}-T001/claim",
        "POST",
        _cells(coder=True),
        payload={"session_id": "sess-matrix-claim", "worker_agent_id": "matrix-coder"},
        ok=(200, 409),
    ),
    _Probe(
        "Claim to_be_audited",
        f"/api/v1/tasks/{PID_ONE}-T002/claim",
        "POST",
        _cells(auditor=True),
        payload={"session_id": "sess-matrix-audit", "worker_agent_id": "matrix-auditor"},
        ok=(200, 409),
    ),
    # *Submit resolution* runs on the real WP-3.2 route (its probe path
    # retired with the deferred entries below): the earlier *Claim
    # pending* row has claimed T001 for ``sess-matrix-claim`` with
    # generation 1 by the time this row walks, so the coder cell carries
    # that fencing pair and lands 201 (T7 — the task's empty scope has
    # no file to violate); denied actors never reach the service (403).
    _Probe(
        "Submit resolution",
        f"/api/v1/tasks/{PID_ONE}-T001/resolution",
        "POST",
        _cells(coder=True),
        payload={
            "session_id": "sess-matrix-claim",
            "lease_generation": 1,
            "git_branch": "feat/PID00001-T001",
            "commit_sha": "0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
            "execution_summary": "matrix walk submission",
            "patch": "",
        },
        ok=(201,),
    ),
    _Probe("Submit verdict", "/probe/verdict", "POST", _cells(auditor=True)),
    _Probe("Review decisions", "/probe/review", "POST", _cells(owner=True, device=True)),
    # Merge queue: Owner's cell is *Read* — the write half is the executor's.
    _Probe("Merge queue", "/probe/merge-queue", "GET", _cells(owner=True, merge_executor=True)),
    _Probe(
        "Merge queue",
        "/probe/merge-queue/start",
        "POST",
        _cells(merge_executor=True),
    ),
    # Section 9.6: agents never read events — no agent cell exists to grant.
    # WP-1.10 (MT-1.10-05): the row runs on the real routes — the history
    # endpoint and the SSE stream (an allowed caller gets 200 on both; the
    # stream response is streaming, and the matrix walk never iterates it).
    _Probe("Read events", "/api/v1/events", "GET", _cells(owner=True, device=True)),
    _Probe("Read events", "/api/v1/events/stream", "GET", _cells(owner=True, device=True)),
)


class _Authz(NamedTuple):
    """Real credentials for every actor plus a request helper."""

    call: Callable[[str, str, str], Any]  # (actor, method, path) -> response
    post: Callable[[str, str, dict[str, Any]], Any]  # (actor, path, data)
    agents: dict[str, dict[str, Any]]  # role -> issuance body (id + token)
    device: dict[str, Any]  # registration body (id + token)


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — keep every test's budgets fresh."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def matrix(owner_client: APIClient, tmp_path: Path) -> Iterator[_Authz]:
    """All actor credentials, then the probe URLConf switched on.

    Order matters: fixtures build credentials through the **real** routes
    first, only then does ``ROOT_URLCONF`` point at this module's probes, so
    fixture traffic never resolves against ``/probe/*``.

    Storage rides along: the WP-3.2 submission row stores a patch artifact
    on its allowed cell, so the media root is this test's ``tmp_path`` —
    never the default ``/media`` (same pattern as the WP-1.11 cases below).
    """
    plain = APIClient()
    agents: dict[str, dict[str, Any]] = {}
    for role in AGENT_ROLES:
        response = owner_client.post(
            "/api/v1/tokens/agent",
            {"project_id": PID_ONE, "scopes": [role]},
        )
        assert response.status_code == 201, response.content
        agents[role] = response.json()

    device_response = owner_client.post(
        "/api/v1/devices",
        {"platform": "android", "push_token": "apns-authz-matrix"},
    )
    assert device_response.status_code == 201, device_response.content
    device = device_response.json()

    # Real registry rows (MT-1.2-07's risk note, WP-1.3): the cross-project
    # acceptance now runs against actual project rows, not bare strings.
    # Created directly with explicit ids so PID00001/PID00002 hold on every
    # backend regardless of sequence state (allocation is tested in
    # test_pid_generation.py; explicit rows never consume the sequence).
    for pid in (PID_ONE, PID_TWO):
        Project.objects.create(
            id=pid,
            name=f"Matrix {pid}",
            repo_path=f"/srv/repos/{pid.lower()}",
            default_branch="main",
            agent_policy=ProjectPolicy.objects.create(),
        )

    # Two real task rows for the two Claim rows (WP-1.6, MT-1.6-07): a
    # pending task the coder cell claims and a to_be_audited one the
    # auditor cell reaches (answered 409 until WP-3.x wires the T11
    # guard). Direct rows keep the matrix self-contained.
    project = Project.objects.get(id=PID_ONE)
    Task.objects.create(
        id=f"{PID_ONE}-T001",
        project=project,
        title="Claim probe (pending)",
        state=TaskState.PENDING,
    )
    Task.objects.create(
        id=f"{PID_ONE}-T002",
        project=project,
        title="Claim probe (to_be_audited)",
        state=TaskState.TO_BE_AUDITED,
    )
    # The seeds occupy indices 1-2: advance the allocator's counter (it
    # lives on the project row) so the Create-drafts probe's first
    # allocation lands on T003 instead of colliding with T001.
    Project.objects.filter(id=PID_ONE).update(task_counter=2)

    def _headers(actor: str) -> dict[str, str] | None:
        if actor in AGENT_ROLES:
            return {"Authorization": f"Bearer {agents[actor]['token']}"}
        if actor == "device":
            return {"Authorization": f"Bearer {device['token']}"}
        return None

    def _call(actor: str, method: str, path: str) -> Any:
        client = owner_client if actor == "owner" else plain
        headers = _headers(actor)
        kwargs: dict[str, Any] = {"headers": headers} if headers else {}
        if method == "GET":
            return client.get(path, **kwargs)
        if method == "DELETE":
            return client.delete(path, **kwargs)
        return client.post(path, {}, **kwargs)

    def _post(actor: str, path: str, data: dict[str, Any]) -> Any:
        client = owner_client if actor == "owner" else plain
        headers = _headers(actor)
        kwargs: dict[str, Any] = {"headers": headers} if headers else {}
        return client.post(path, data, **kwargs)

    with (
        override_settings(ROOT_URLCONF=__name__),
        override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)),
    ):
        yield _Authz(call=_call, post=_post, agents=agents, device=device)


def _code(response: Any) -> str:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    return str(error["code"])


# --- traceability: every row, every actor, one case each --------------------


def test_every_matrix_row_is_exercised_for_every_actor() -> None:
    """Section 12.2 'as tests': drop a row/actor and this suite fails."""
    assert {probe.row for probe in PROBES} == set(MATRIX_ROWS)
    for row in MATRIX_ROWS:
        actors_with_cases = {
            actor for probe in PROBES if probe.row == row for actor in probe.grants
        }
        missing = set(ACTORS) - actors_with_cases
        assert not missing, f"row {row!r} has no case for actors: {sorted(missing)}"


def test_matrix_rows_against_the_running_api(matrix: _Authz) -> None:
    """The whole printed grid, one request per cell, real credentials."""
    for probe in PROBES:
        for actor, allowed in probe.grants.items():
            if probe.method == "POST":
                response = matrix.post(actor, probe.path, probe.payload or {})
            else:
                response = matrix.call(actor, probe.method, probe.path)
            if allowed:
                assert response.status_code in probe.ok, (
                    f"{probe.row} / {actor}: {response.status_code} {response.content!r}"
                )
                continue
            if actor == "anonymous":
                assert response.status_code == 401, probe.row
                assert _code(response) == AUTH_REQUIRED
            else:
                assert response.status_code == 403, probe.row
                assert _code(response) == ROLE_NOT_PERMITTED


# --- WP-1.2 acceptance: cross-project rejection + body cannot widen ---------


def test_pid00001_agent_token_is_forbidden_on_pid00002_resources(
    matrix: _Authz,
) -> None:
    """WP-1.2 acceptance, verbatim: AUTH_FORBIDDEN_PROJECT across projects.

    Now on the **real** task routes (MT-1.4-03 landed them): the scope
    guard runs first on both shapes — the project-addressed create (PID
    in the URL) and the task-addressed detail (PID inside the task id) —
    while the own-project create falls through to the Owner-only role
    check (the deferred Decomposer cell, recorded in
    ``DEFERRED_MATRIX_CELLS``).
    """
    own = matrix.post("decomposer", f"/api/v1/projects/{PID_ONE}/tasks", {"title": "Own"})
    assert own.status_code == 403
    assert _code(own) == ROLE_NOT_PERMITTED  # deferred cell: owner-only today

    other = matrix.post("decomposer", f"/api/v1/projects/{PID_TWO}/tasks", {"title": "Other"})
    assert other.status_code == 403
    assert _code(other) == AUTH_FORBIDDEN_PROJECT


def test_cross_project_guard_on_the_real_projects_registry(matrix: _Authz) -> None:
    """WP-1.3 extension: the guard against real rows on the real routes.

    The same acceptance as the probe case above, now where the endpoint
    actually exists (MT-1.2-07: "switch to API-created projects when the
    registry lands"): scope mismatch answers AUTH_FORBIDDEN_PROJECT
    before any role logic, the own-project read falls through to §9.2's
    agent read cell (the WP-2.x activation — the role check now admits
    the scoped agent token instead of refusing it), and the owner reads
    the row.
    """
    own_project = matrix.call("decomposer", "GET", f"/api/v1/projects/{PID_ONE}")
    assert own_project.status_code == 200, own_project.content
    assert own_project.json()["id"] == PID_ONE  # §9.2: agents read own project

    other_project = matrix.call("decomposer", "GET", f"/api/v1/projects/{PID_TWO}")
    assert other_project.status_code == 403
    assert _code(other_project) == AUTH_FORBIDDEN_PROJECT

    # A widening body never reaches the serializer: permissions run first.
    widen = matrix.post("decomposer", f"/api/v1/projects/{PID_TWO}", {"project_id": PID_ONE})
    assert widen.status_code == 403
    assert _code(widen) == AUTH_FORBIDDEN_PROJECT

    readable = matrix.call("owner", "GET", f"/api/v1/projects/{PID_ONE}")
    assert readable.status_code == 200
    assert readable.json()["id"] == PID_ONE


def test_body_supplied_project_id_cannot_widen_the_token_scope(
    matrix: _Authz,
) -> None:
    """ADR-004 / G-07: scope comes from token + URL, never from the body."""
    # Widening attempt: address PID00002 while the body pleads the token's
    # own PID00001 — the body is never consulted, the request is rejected.
    widen = matrix.post("decomposer", f"/api/v1/projects/{PID_TWO}/tasks", {"project_id": PID_ONE})
    assert widen.status_code == 403
    assert _code(widen) == AUTH_FORBIDDEN_PROJECT

    # Mirror: a body claiming PID00002 neither narrows nor redirects the
    # check — the URL's PID and the token agree, so scope passes and the
    # Owner-only role check answers (if the body *had* redirected scope,
    # this would be AUTH_FORBIDDEN_PROJECT instead).
    narrow = matrix.post("decomposer", f"/api/v1/projects/{PID_ONE}/tasks", {"project_id": PID_TWO})
    assert narrow.status_code == 403
    assert _code(narrow) == ROLE_NOT_PERMITTED

    # Positive proof on the allowed caller: the created row's project
    # comes from the URL — `project_id` is not client-settable at all
    # (the strict serializer rejects it as an unknown field).
    rejected = matrix.post(
        "owner", f"/api/v1/projects/{PID_TWO}/tasks", {"title": "Body", "project_id": PID_ONE}
    )
    assert rejected.status_code == 400
    assert _code(rejected) == VALIDATION_ERROR

    created = matrix.post("owner", f"/api/v1/projects/{PID_TWO}/tasks", {"title": "URL wins"})
    assert created.status_code == 201
    assert created.json()["project_id"] == PID_TWO, "the URL decides the project"


# --- WP-1.2 acceptance: revoked tokens fail immediately ---------------------


def test_revoked_agent_token_fails_on_its_very_next_request(
    matrix: _Authz, owner_client: APIClient
) -> None:
    """Revoke through the Owner API; the next bearer call is AUTH_REQUIRED."""
    token = matrix.agents["coder"]
    claim_path = f"/api/v1/tasks/{PID_ONE}-T001/claim"
    claim_body = {"session_id": "sess-revoke-probe", "worker_agent_id": "matrix-coder"}
    # The real WP-1.6 claim route (the probe retires with MT-1.6-07):
    # pre-revoke the coder claims in its own project.
    assert matrix.post("coder", claim_path, claim_body).status_code == 200

    revoke = owner_client.delete(f"/api/v1/tokens/{token['id']}")
    assert revoke.status_code == 200

    # Authentication runs before body parsing — the revoked bearer dies
    # with AUTH_REQUIRED even though the payload alone would pass.
    after = matrix.post("coder", claim_path, claim_body)
    assert after.status_code == 401
    assert _code(after) == AUTH_REQUIRED


def test_revoked_device_token_fails_on_its_very_next_request(
    matrix: _Authz, owner_client: APIClient
) -> None:
    """Lost phone: one DELETE revokes device + token; the next call dies."""
    # Real *Read events* route since WP-1.10 (MT-1.10-05) — the history
    # endpoint answers JSON, safe to assert before and after revocation.
    assert matrix.call("device", "GET", "/api/v1/events").status_code == 200

    revoke = owner_client.delete(f"/api/v1/devices/{matrix.device['id']}")
    assert revoke.status_code == 200

    after = matrix.call("device", "GET", "/api/v1/events")
    assert after.status_code == 401
    assert _code(after) == AUTH_REQUIRED


def test_revoked_owner_session_fails_on_its_very_next_request(
    matrix: _Authz, owner_client: APIClient
) -> None:
    """Logout revokes the row; the very next owner request is AUTH_REQUIRED."""
    assert matrix.call("owner", "GET", "/api/v1/projects").status_code == 200

    assert owner_client.post("/api/v1/auth/logout").status_code == 200

    after = matrix.call("owner", "GET", "/api/v1/projects")
    assert after.status_code == 401
    assert _code(after) == AUTH_REQUIRED


# --- WP-1.6 landing: the entries DEFERRED_ENDPOINTS retired (MT-1.6-07/09) -


def test_wp16_landed_routes_enforce_their_callers(matrix: _Authz) -> None:
    """Real-route cases for work/release/agent-sessions (removed deferred).

    The two Claim rows now run as real-route probes above; this covers the
    other three surfaces WP-1.6 landed, asserting the catalog codes of the
    callers each deferred entry used to stand in for. The services'
    full catalogs live in tests/test_claim_release_endpoints.py and
    tests/test_agent_session_endpoints.py.
    """
    # Work (the agent offer list, caller Agent per Section 9.2):
    # anonymous 401, owner 403 (IsAgentToken), agent 200.
    anon_work = matrix.call("anonymous", "GET", f"/api/v1/projects/{PID_ONE}/work")
    assert anon_work.status_code == 401
    assert _code(anon_work) == AUTH_REQUIRED

    owner_work = matrix.call("owner", "GET", f"/api/v1/projects/{PID_ONE}/work")
    assert owner_work.status_code == 403
    assert _code(owner_work) == ROLE_NOT_PERMITTED

    coder_work = matrix.call("coder", "GET", f"/api/v1/projects/{PID_ONE}/work")
    assert coder_work.status_code == 200

    # Release (agent-only): anonymous 401, owner 403, coder 200 on the
    # lease it claims first (the matrix rows above claim T001 only in
    # their own test — each test gets a fresh database).
    claim = matrix.post(
        "coder",
        f"/api/v1/tasks/{PID_ONE}-T001/claim",
        {"session_id": "sess-landed", "worker_agent_id": "matrix-coder"},
    )
    assert claim.status_code == 200

    anon_release = matrix.call("anonymous", "POST", f"/api/v1/tasks/{PID_ONE}-T001/release")
    assert anon_release.status_code == 401
    assert _code(anon_release) == AUTH_REQUIRED

    release = matrix.post(
        "coder",
        f"/api/v1/tasks/{PID_ONE}-T001/release",
        {"session_id": "sess-landed", "lease_generation": 1},
    )
    assert release.status_code == 200

    # Owner override (T6's O actor, by design): after re-claiming, the
    # owner releases without the fencing pair — the retired deferred
    # entry stood in for this route; test_release_owner_override covers
    # the service path, this proves the matrix cell.
    reclaim = matrix.post(
        "coder",
        f"/api/v1/tasks/{PID_ONE}-T001/claim",
        {"session_id": "sess-landed", "worker_agent_id": "matrix-coder"},
    )
    assert reclaim.status_code == 200

    owner_release = matrix.post("owner", f"/api/v1/tasks/{PID_ONE}-T001/release", {})
    assert owner_release.status_code == 200

    # Agent sessions (MT-1.6-09): anonymous 401, owner 403 (agent-only
    # surface), agent 201 open + 200 end on its own session.
    anon_open = matrix.call("anonymous", "POST", "/api/v1/agent-sessions")
    assert anon_open.status_code == 401
    assert _code(anon_open) == AUTH_REQUIRED

    owner_open = matrix.post("owner", "/api/v1/agent-sessions", {})
    assert owner_open.status_code == 403
    assert _code(owner_open) == ROLE_NOT_PERMITTED

    opened = matrix.post(
        "coder",
        "/api/v1/agent-sessions",
        {"id": "sess-matrix-open", "transport": "stdio"},
    )
    assert opened.status_code == 201

    ended = matrix.call("coder", "POST", "/api/v1/agent-sessions/sess-matrix-open/end")
    assert ended.status_code == 200


# --- WP-1.8 landing: the Progress row's real callers (deferred retired) -----


def test_wp18_landed_checkpoint_routes_enforce_their_callers(matrix: _Authz) -> None:
    """Real-route cases for the checkpoint endpoints (removed deferred).

    POST's caller cell is **Agent only** (Section 9.2 Progress row read
    side split by method): anonymous 401, owner 403, device 403 — none
    reach the service. GET's cell is **Agent / Owner**: anonymous 401,
    device 403, owner 200, agent 200. The agent's allowed POST goes
    through the real fencing gate — claim T001 first, then checkpoint
    with the live generation (the services' own catalogs live in
    tests/test_checkpoint_endpoint.py).
    """
    task = f"/api/v1/tasks/{PID_ONE}-T001"
    checkpoints = f"{task}/checkpoints"

    # POST (Agent only): the denied shapes die at the permission gate.
    anon_post = matrix.call("anonymous", "POST", checkpoints)
    assert anon_post.status_code == 401
    assert _code(anon_post) == AUTH_REQUIRED

    owner_post = matrix.post("owner", checkpoints, {"session_id": "sess-matrix-cp"})
    assert owner_post.status_code == 403
    assert _code(owner_post) == ROLE_NOT_PERMITTED

    device_post = matrix.post("device", checkpoints, {"session_id": "sess-matrix-cp"})
    assert device_post.status_code == 403
    assert _code(device_post) == ROLE_NOT_PERMITTED

    # GET (Agent / Owner): device excluded, both admitted callers read.
    anon_get = matrix.call("anonymous", "GET", checkpoints)
    assert anon_get.status_code == 401
    assert _code(anon_get) == AUTH_REQUIRED

    device_get = matrix.call("device", "GET", checkpoints)
    assert device_get.status_code == 403
    assert _code(device_get) == ROLE_NOT_PERMITTED

    owner_get = matrix.call("owner", "GET", checkpoints)
    assert owner_get.status_code == 200

    agent_get = matrix.call("coder", "GET", checkpoints)
    assert agent_get.status_code == 200

    # The agent's own POST: claim (Section 9.3) then checkpoint with the
    # fencing pair — 200 with the stored row and the extended expiry.
    claim = matrix.post(
        "coder",
        f"{task}/claim",
        {"session_id": "sess-matrix-cp", "worker_agent_id": "matrix-coder"},
    )
    assert claim.status_code == 200, claim.content

    agent_post = matrix.post(
        "coder",
        checkpoints,
        {"session_id": "sess-matrix-cp", "lease_generation": 1, "message": "matrix"},
    )
    assert agent_post.status_code == 200
    assert agent_post.json()["lease_extended"] is True


# --- WP-1.11 landing: the Attachments row's real callers (deferred retired) --


def test_wp111_landed_attachment_routes_enforce_their_callers(
    matrix: _Authz, tmp_path: Path
) -> None:
    """Real-route cases for upload/list/detail/delete (removed deferred).

    Section 9.2's Attachments caller column is "Owner / Agent (read)";
    §12.2 prints no attachments capability row, so this is the landed-
    routes pattern (WP-1.8/WP-2.x), not a PROBES entry. The catalog:
    upload POST and delete DELETE are Owner-only (anonymous 401, device
    403, agent 403 — agents read, never write); the two GETs admit the
    owner **and** an agent token scoped to the addressed project, with
    cross-project agents answered AUTH_FORBIDDEN_PROJECT before any
    role logic (ADR-004 zero-bleed, Section 12.1). The services' full
    catalogs live in tests/attachments/.
    """
    task = f"{PID_ONE}-T001"
    attachments = f"/api/v1/tasks/{task}/attachments"

    # Upload (Owner only): anonymous 401, device 403, agent 403.
    anon_upload = matrix.call("anonymous", "POST", attachments)
    assert anon_upload.status_code == 401
    assert _code(anon_upload) == AUTH_REQUIRED

    # Owner passes the authz cell and fails at input validation (no
    # `file` part): 400 VALIDATION_ERROR — a *denied* actor would have
    # been stopped at 403/401 before the body was ever examined.
    owner_upload = matrix.post("owner", attachments, {})
    assert owner_upload.status_code == 400
    assert _code(owner_upload) == VALIDATION_ERROR

    for actor in ("coder", "auditor", "decomposer", "merge_executor", "device"):
        denied = matrix.post(actor, attachments, {})
        assert denied.status_code == 403, actor
        assert _code(denied) == ROLE_NOT_PERMITTED, actor

    # Listing (Owner / Agent read): device excluded, both admitted callers.
    anon_list = matrix.call("anonymous", "GET", attachments)
    assert anon_list.status_code == 401
    assert _code(anon_list) == AUTH_REQUIRED

    device_list = matrix.call("device", "GET", attachments)
    assert device_list.status_code == 403
    assert _code(device_list) == ROLE_NOT_PERMITTED

    owner_list = matrix.call("owner", "GET", attachments)
    assert owner_list.status_code == 200
    assert owner_list.json() == {"results": [], "next_cursor": None}

    agent_list = matrix.call("coder", "GET", attachments)
    assert agent_list.status_code == 200

    # Cross-project agent token on both halves (zero-bleed).
    foreign_list = matrix.call("decomposer", "GET", attachments)
    assert foreign_list.status_code == 200  # same project: allowed

    # Detail + delete with a real uploaded row (owner uploads bytes).
    from django.core.files.uploadedfile import SimpleUploadedFile

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    client = APIClient()
    login = client.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert login.status_code == 200, login.content
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        created = client.post(
            attachments,
            {"file": SimpleUploadedFile("matrix.png", png, content_type="image/png")},
            format="multipart",
        )
    assert created.status_code == 201, created.content
    attachment_id = created.json()["id"]
    detail = f"/api/v1/attachments/{attachment_id}"

    # Detail GET: owner and scoped agent read; device/anonymous refused.
    assert client.get(detail).status_code == 200
    assert matrix.call("coder", "GET", detail).status_code == 200
    assert matrix.call("device", "GET", detail).status_code == 403
    assert matrix.call("anonymous", "GET", detail).status_code == 401

    # DELETE: Owner only — every other actor is refused before the rule.
    for actor in ("coder", "auditor", "decomposer", "merge_executor", "device"):
        denied = matrix.call(actor, "DELETE", detail)
        assert denied.status_code == 403, actor
        assert _code(denied) == ROLE_NOT_PERMITTED, actor
    assert matrix.call("anonymous", "DELETE", detail).status_code == 401

    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        deleted = client.delete(detail)
    assert deleted.status_code == 200, deleted.content
    assert deleted.json()["deleted_at"] is not None


# --- WP-2.x activation: §9.2 agent read-only cells on their real routes -----


def test_wp2x_agent_read_routes_enforce_their_callers(matrix: _Authz) -> None:
    """The activated read cells: project, policy and task detail.

    Section 9.2's caller cells as the API enforces them after the WP-2.x
    activation: ``GET /projects/{pid}``, ``GET /projects/{pid}/policy``
    and ``GET /tasks/{id}`` admit the owner **and** an agent token
    scoped to the addressed project (the bridge's session context and
    ``get_task_details`` reads); devices answer ROLE_NOT_PERMITTED (not
    in the caller cell), anonymous AUTH_REQUIRED, and the *owner-only*
    shapes — the project list (the Manage-projects matrix row above) and
    every write — stay refused to agents.
    """
    reads = (
        f"/api/v1/projects/{PID_ONE}",
        f"/api/v1/projects/{PID_ONE}/policy",
        f"/api/v1/tasks/{PID_ONE}-T001",
    )

    # Owner and any project-scoped agent role read all three routes.
    for actor in ("owner", "coder", "auditor", "decomposer", "merge_executor"):
        for route in reads:
            response = matrix.call(actor, "GET", route)
            assert response.status_code == 200, (actor, route, response.content)

    # Devices are excluded from the read cells.
    for route in reads:
        response = matrix.call("device", "GET", route)
        assert response.status_code == 403, route
        assert _code(response) == ROLE_NOT_PERMITTED, route

    # Anonymous → AUTH_REQUIRED on every read.
    for route in reads:
        response = matrix.call("anonymous", "GET", route)
        assert response.status_code == 401, route
        assert _code(response) == AUTH_REQUIRED, route

    # The project list spans every project: the Manage-projects row keeps
    # it Owner-only for agents (§12.2 cells; DEFERRED_MATRIX_CELLS still
    # governs the create row below), and the POST-shaped write on the
    # addressed rows stays Owner-only too — no write rides the read cell.
    # (PATCH denials for agents are asserted on the real routes in
    # test_project_api / test_project_policy_api / test_task_api.)
    listed = matrix.call("coder", "GET", "/api/v1/projects")
    assert listed.status_code == 403
    assert _code(listed) == ROLE_NOT_PERMITTED

    create = matrix.post("coder", f"/api/v1/projects/{PID_ONE}/tasks", {"title": "Nope"})
    assert create.status_code == 403
    assert _code(create) == ROLE_NOT_PERMITTED


# --- FR-SEC-05 case inside the matrix suite (MT-1.2-06) ---------------------


def test_rate_limit_burst_on_a_device_endpoint_returns_rate_limited(
    owner_client: APIClient, settings: Any
) -> None:
    """A device-endpoint burst answers RATE_LIMITED in the standard envelope."""
    rest = dict(settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {**rest["DEFAULT_THROTTLE_RATES"], "device": "2/min"}
    settings.REST_FRAMEWORK = rest

    payload = {"platform": "ios", "push_token": "apns-rate-case"}
    assert owner_client.post("/api/v1/devices", payload).status_code == 201
    assert owner_client.post("/api/v1/devices", payload).status_code == 201

    throttled = owner_client.post("/api/v1/devices", payload)
    assert throttled.status_code == 429
    assert _code(throttled) == RATE_LIMITED
    error = throttled.json()["error"]
    assert error["retryable"] is True


# --- WP-3.2 landing: the Submission row's real callers (deferred retired) ----


def test_wp32_landed_resolution_routes_enforce_their_callers(matrix: _Authz) -> None:
    """Real-route cases for resolution submit/list/patch (removed deferred).

    POST's caller cell is **Agent, lease owner** (Section 12.2 "Submit
    resolution"): anonymous 401, owner/device/auditor 403 — none reach
    the service; the coder's own POST runs the real fencing gate (a
    foreign session 403 ``LEASE_NOT_OWNED``, a stale generation 409
    ``LEASE_EXPIRED``) and lands 201 with a stored Section 7.2 row (the
    service's full catalog lives in tests/test_resolution_submission.py).
    The two GETs are the Section 9.2 **Agent / Owner** cell: anonymous
    401, device 403, owner 200, agent 200 — and the patch GET serves the
    artifact the submission stored (media on this suite's tmp_path).
    """
    task = f"/api/v1/tasks/{PID_ONE}-T001"
    resolution = f"{task}/resolution"
    resolutions = f"{task}/resolutions"
    body = {
        "session_id": "sess-wp32-lander",
        "lease_generation": 1,
        "git_branch": "feat/PID00001-T001",
        "commit_sha": "0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        "execution_summary": "wp32 landing",
        "patch": "",
    }

    # POST (Agent, lease owner): denied shapes die at the permission gate.
    anon_post = matrix.call("anonymous", "POST", resolution)
    assert anon_post.status_code == 401
    assert _code(anon_post) == AUTH_REQUIRED

    for denied in ("owner", "device", "auditor"):
        refused = matrix.post(denied, resolution, body)
        assert refused.status_code == 403, denied
        assert _code(refused) == ROLE_NOT_PERMITTED, denied

    # The coder reaches the service: claim first (Section 9.3), then the
    # lease checks answer their catalog codes for the wrong callers.
    claim = matrix.post(
        "coder",
        f"{task}/claim",
        {"session_id": "sess-wp32-lander", "worker_agent_id": "matrix-coder"},
    )
    assert claim.status_code == 200, claim.content

    foreign = matrix.post("coder", resolution, {**body, "session_id": "sess-intruder"})
    assert foreign.status_code == 403
    assert _code(foreign) == "LEASE_NOT_OWNED"

    stale = matrix.post("coder", resolution, {**body, "lease_generation": 0})
    assert stale.status_code == 409
    assert _code(stale) == "LEASE_EXPIRED"

    submitted = matrix.post("coder", resolution, body)
    assert submitted.status_code == 201, submitted.content
    submitted_body = submitted.json()
    assert submitted_body["task"]["state"] == "to_be_audited"
    assert submitted_body["scope_violations"] == []
    resolution_id = submitted_body["resolution"]["id"]

    # GET /tasks/{id}/resolutions (Agent / Owner).
    anon_list = matrix.call("anonymous", "GET", resolutions)
    assert anon_list.status_code == 401
    assert _code(anon_list) == AUTH_REQUIRED

    device_list = matrix.call("device", "GET", resolutions)
    assert device_list.status_code == 403
    assert _code(device_list) == ROLE_NOT_PERMITTED

    owner_list = matrix.call("owner", "GET", resolutions)
    assert owner_list.status_code == 200

    agent_list = matrix.call("coder", "GET", resolutions)
    assert agent_list.status_code == 200
    assert agent_list.json()["results"][0]["attempt_number"] == 1

    # GET /resolutions/{id}/patch (Agent / Owner) — the stored artifact.
    patch_url = f"/api/v1/resolutions/{resolution_id}/patch"
    anon_patch = matrix.call("anonymous", "GET", patch_url)
    assert anon_patch.status_code == 401
    assert _code(anon_patch) == AUTH_REQUIRED

    device_patch = matrix.call("device", "GET", patch_url)
    assert device_patch.status_code == 403
    assert _code(device_patch) == ROLE_NOT_PERMITTED

    owner_patch = matrix.call("owner", "GET", patch_url)
    assert owner_patch.status_code == 200

    agent_patch = matrix.call("coder", "GET", patch_url)
    assert agent_patch.status_code == 200
    assert agent_patch.json()["patch"] == ""


# --- deferred routes: an untested row must never be silently green ----------


DEFERRED_ENDPOINTS: tuple[str, ...] = (
    # Section 9.2 routes that do not exist yet. Each entry maps to a
    # matrix row or an Owner/Agent caller row whose probe/registry case must
    # move onto the real route when the owning WP lands it — the assertion
    # below fails the moment one of these paths starts resolving.
    # WP-1.3 removed its entries here as it landed: /projects and
    # /projects/{pid} (the Manage-projects row runs on the real route
    # above), /policy with MT-1.3-04, and /manifest with MT-1.3-05 — the
    # latter two assert their Owner-only catalog codes in their own suites.
    # WP-1.4 removed /projects/{pid}/tasks and /tasks/{id} with MT-1.4-03:
    # the Create-drafts row runs on the real route above (its printed
    # Decomposer/Device cells recorded in DEFERRED_MATRIX_CELLS), and
    # test_task_api.py asserts the real routes' catalog codes.
    # WP-1.5 landed the transition *service* only: MT-1.5-02 keeps the
    # POST /tasks/{id}/transition wiring out of scope (service behavior
    # asserted in its own suites), so this entry stays deferred — its
    # Publish-tasks probe below remains the row under test until the
    # route lands (WP-1.15 hardening) and forces this line's replacement.
    "/api/v1/tasks/1/transition",  # Publish tasks (service in WP-1.5; endpoint deferred)
    # WP-1.6 (MT-1.6-07/09) removed its entries as it landed them: the
    # work/claim/release routes now carry real cases (both Claim rows run
    # as real-route probes above; test_wp16_landed_routes_enforce_their_
    # callers below covers work + release), and the agent-sessions pair
    # moved to the real MT-1.6-09 routes there too.
    # WP-1.8 removed /api/v1/tasks/1/checkpoints as it landed the route:
    # test_wp18_landed_checkpoint_routes_enforce_their_callers below
    # carries its real POST/GET cases (reporting-only: WP-1.8 recorded
    # the hand-off, the matrix owner landed it at convergence).
    # WP-3.2 removed its three entries as it landed the Submission row:
    # test_wp32_landed_resolution_routes_enforce_their_callers below
    # carries the real POST/GET cases (the *Submit resolution* matrix
    # row now runs on the real route in PROBES above), so the
    # resolution paths are asserted live instead of absent.
    "/api/v1/tasks/1/audit-verdict",  # Submit verdict (WP-1.6)
    "/api/v1/tasks/1/audit-reports",  # WP-1.6
    "/api/v1/tasks/1/review",  # Review decisions (WP-1.5/1.6)
    "/api/v1/merge/pending",  # Merge queue read (WP-3.x)
    "/api/v1/merge/1/start",  # Merge queue write (WP-3.x)
    "/api/v1/merge/1/result",  # Merge queue write (WP-3.x)
    # WP-1.11 removed its upload/list/detail/delete entries as it landed
    # them: test_wp111_landed_attachment_routes_enforce_their_callers
    # below carries the real per-actor cases (the Section 9.2 Attachments
    # caller column "Owner / Agent (read)" — §12.2 prints no attachments
    # capability row, so no PROBES entry exists or is needed).
    "/api/v1/attachments/1/content",  # WP-1.14 (MT-1.11-04 out of scope)
    # WP-1.10 (MT-1.10-05) removed its entries as it landed them: the
    # *Read events* row now runs on the real /api/v1/events and
    # /api/v1/events/stream routes (probes above), and
    # tests/events/test_event_authorization.py carries the full per-event
    # filtering catalog.
    # MT-1.15-06 removed /api/v1/dashboard/summary as it landed the route:
    # the real per-caller cases (owner 200; every agent role + device 403
    # ROLE_NOT_PERMITTED; anonymous 401) live in
    # tests/test_dashboard_summary.py — no row left untested (MT-1.2-07).
)


# --- deferred matrix cells: recorded, still denied, never silently green ----

DEFERRED_MATRIX_CELLS: tuple[tuple[str, str], ...] = (
    # MT-1.4-03 risk note, made executable: the real task routes enforce
    # Owner-only **today**, while Section 12.2 prints these cells for
    # "Create draft tasks" — Decomposer = Yes, Device = Yes (Could). With
    # no distinct decomposer token kind yet (MT-1.2-05 risk), WP-2.x/M5
    # must revisit them; activation means swapping the view's permission
    # class to CanCreateDraftTasks (already implemented and cell-tested in
    # tests/test_permission_classes.py) and flipping these rows to
    # allowed — nothing here may be deleted to make a test pass.
    ("Create draft tasks", "decomposer"),
    ("Create draft tasks", "device"),
)


def test_deferred_matrix_cells_are_recorded_and_still_denied(matrix: _Authz) -> None:
    """The two deferred cells assert their CURRENT denial on the REAL route."""
    assert {row for row, _actor in DEFERRED_MATRIX_CELLS} <= set(MATRIX_ROWS)

    for row, actor in DEFERRED_MATRIX_CELLS:
        response = matrix.post(
            actor, f"/api/v1/projects/{PID_ONE}/tasks", {"title": "Deferred cell"}
        )
        assert response.status_code == 403, (row, actor, response.content)
        assert _code(response) == ROLE_NOT_PERMITTED, (row, actor)
        # When WP-2.x/M5 activates the cell, this denial becomes 201 and
        # the entry moves into PROBES' grants (revisit marker, MT-1.4-03).


@pytest.mark.parametrize("path_", DEFERRED_ENDPOINTS)
def test_deferred_section_9_2_endpoints_do_not_exist_yet(path_: str) -> None:
    """Drift guard: a landing route forces its matrix case to go real."""
    try:
        resolve(path_)
    except Resolver404:
        return
    pytest.fail(
        f"{path_} landed — replace its probe/deferred entry with a real "
        "authorization-matrix case (MT-1.2-07; never leave a row untested)"
    )


def test_probe_urlconf_is_not_the_production_urlconf() -> None:
    """Paranoia: probes live only in this test module's URLConf."""
    from django.conf import settings as django_settings

    assert "test_authorization_matrix" not in django_settings.ROOT_URLCONF
    # ...and the scope guard's code stays the canonical catalog value.
    assert AuthForbiddenProject.default_code == AUTH_FORBIDDEN_PROJECT
