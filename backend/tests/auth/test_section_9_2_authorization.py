"""MT-1.15-04 — the Section 9.2 endpoint-permission enumeration contract.

Consolidation, not duplication (Section 19.6): MT-1.2-07's behavioral matrix
stays in ``tests/test_authorization_matrix.py`` — imported by reference here
and run in the same WP-1.15 gate — while this module owns the *enumeration*
that suite does not carry:

* the parent plan's Section 9.2 endpoint table is parsed at test time, so the
  row set can never drift from the plan text (the plan, not this file, is the
  single source of truth);
* every operation in the **generated OpenAPI document** (MT-1.1-04's surface)
  must carry a Section 9.2 row or sit in the explicit ``GAPS`` list — a new
  endpoint without a permission row fails this suite (the MT risk note);
* every row either resolves in the production URLConf or is deferred in the
  adopted ``DEFERRED_ENDPOINTS`` drift guard, checked in both directions — a
  landing route flips its row here exactly as it does in the adopted file;
* every live row links to the test that behaviorally proves its caller cells
  (the adopted matrix's landed-route cases, the per-WP suites, and this
  package's ``test_attachment_access_paths.py`` for the negative token paths)
  — a row without a proof fails the suite.

Caller cells are derived from the plan's own caller column mapped onto the
Section 12.2 actor kinds the adopted matrix walks (roles taken from the
adopted file, never re-listed).

Run: ``pytest backend/tests/auth/test_section_9_2_authorization.py -v``.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any, NamedTuple, cast

import pytest
from django.urls import Resolver404, resolve
from drf_spectacular.generators import SchemaGenerator

from tests import test_authorization_matrix as adopted

PLAN_PATH = Path(__file__).resolve().parents[3] / "ai_agent_task_orchestrator_architecture_plan.md"

#: Every operation the backend serves must carry a Section 9.2 row. GAPS holds
#: the endpoints that exist in the generated OpenAPI document but print no
#: plan row — each entry is a *documented plan gap*, never a silent allowance:
#: when the plan gains the row, the gap entry must be deleted (the gap test
#: below fails while it lingers). ``GET /api/v1/devices`` is the sole entry:
#: the device list landed with WP-1.2's devices surface, the Section 9.2
#: Devices row prints only POST/DELETE, and the omission was flagged when the
#: plan-doc series transcribed the table (its case lives in
#: ``tests/test_device_list.py``).
GAPS: frozenset[tuple[str, str]] = frozenset({("GET", "/api/v1/devices")})

#: Rows whose endpoints print in Section 9.2 but do not exist yet. Their
#: "proof" is exactly the adopted drift guard: the sample path below must be a
#: member of ``adopted.DEFERRED_ENDPOINTS`` and must not resolve. The five
#: literals mirror the adopted file's entries; membership is asserted, so an
#: edit there without an edit here fails both directions.
DEFERRED_ROWS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/tasks/{id}/transition"),
        # WP-3.6 removed the review row from this set: POST /tasks/{id}/review
        # landed and its caller cells run on the real route (PROOF below).
        ("GET", "/api/v1/merge/pending"),
        ("POST", "/api/v1/merge/{task}/start"),
        ("POST", "/api/v1/merge/{task}/result"),
    }
)

#: Every non-deferred row (and every GAPS entry) points at the test that
#: behaviorally proves its caller cells — adoption by reference: the pointer
#: must resolve to a real test function, so a renamed or deleted proof fails
#: this suite instead of silently orphaning the row.
PROOF: dict[tuple[str, str], tuple[str, str]] = {
    # --- Auth row (Owner)
    ("POST", "/api/v1/auth/login"): (
        "tests.test_owner_session_auth",
        "test_login_returns_binding_once_and_sets_secure_session_cookies",
    ),
    ("POST", "/api/v1/auth/logout"): (
        "tests.test_owner_session_auth",
        "test_logout_revokes_session_immediately",
    ),
    ("POST", "/api/v1/auth/refresh"): (
        "tests.test_owner_session_auth",
        "test_refresh_extends_session_and_cannot_resurrect_it",
    ),
    # --- Tokens row (Owner)
    ("POST", "/api/v1/tokens/agent"): (
        "tests.test_agent_token_endpoints",
        "test_issue_is_owner_only",
    ),
    ("DELETE", "/api/v1/tokens/{id}"): (
        "tests.test_agent_token_endpoints",
        "test_revoked_token_fails_authentication_on_its_very_next_request",
    ),
    ("GET", "/api/v1/tokens"): ("tests.test_agent_token_endpoints", "test_list_is_owner_only"),
    # --- Devices row (Mobile)
    ("POST", "/api/v1/devices"): ("tests.test_device_registration", "test_register_is_owner_only"),
    ("DELETE", "/api/v1/devices/{id}"): (
        "tests.test_device_revocation",
        "test_only_the_owning_owner_can_revoke",
    ),
    # --- Projects row (Owner; agents read-only for own project)
    ("GET", "/api/v1/projects"): (
        "tests.test_authorization_matrix",
        "test_matrix_rows_against_the_running_api",
    ),
    ("POST", "/api/v1/projects"): (
        "tests.test_project_api",
        "test_create_assigns_a_generated_pid_and_the_default_policy_pair",
    ),
    ("GET", "/api/v1/projects/{pid}"): (
        "tests.test_authorization_matrix",
        "test_wp2x_agent_read_routes_enforce_their_callers",
    ),
    ("PATCH", "/api/v1/projects/{pid}"): (
        "tests.test_project_api",
        "test_patch_updates_each_mutable_fr_prj_02_field",
    ),
    ("GET", "/api/v1/projects/{pid}/manifest"): (
        "tests.test_manifest",
        "test_manifest_endpoint_downloads_a_schema_valid_document",
    ),
    ("GET", "/api/v1/projects/{pid}/policy"): (
        "tests.test_authorization_matrix",
        "test_wp2x_agent_read_routes_enforce_their_callers",
    ),
    ("PATCH", "/api/v1/projects/{pid}/policy"): (
        "tests.test_project_policy_api",
        "test_policy_endpoint_is_owner_only_with_catalog_codes",
    ),
    # --- Tasks row (Owner)
    ("GET", "/api/v1/projects/{pid}/tasks"): (
        "tests.test_task_list",
        "test_list_is_owner_only_with_scope_first",
    ),
    ("POST", "/api/v1/projects/{pid}/tasks"): (
        "tests.test_authorization_matrix",
        "test_matrix_rows_against_the_running_api",
    ),
    ("GET", "/api/v1/tasks/{id}"): (
        "tests.test_authorization_matrix",
        "test_wp2x_agent_read_routes_enforce_their_callers",
    ),
    ("PATCH", "/api/v1/tasks/{id}"): (
        "tests.test_task_api",
        "test_patch_enforces_the_writable_field_allowlist",
    ),
    # --- Agent work row (Agent)
    ("GET", "/api/v1/projects/{pid}/work"): (
        "tests.test_authorization_matrix",
        "test_wp16_landed_routes_enforce_their_callers",
    ),
    ("POST", "/api/v1/tasks/{id}/claim"): (
        "tests.test_authorization_matrix",
        "test_matrix_rows_against_the_running_api",
    ),
    ("POST", "/api/v1/tasks/{id}/release"): (
        "tests.test_authorization_matrix",
        "test_wp16_landed_routes_enforce_their_callers",
    ),
    # --- Progress row (Agent / Owner)
    ("POST", "/api/v1/tasks/{id}/checkpoints"): (
        "tests.test_authorization_matrix",
        "test_wp18_landed_checkpoint_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/tasks/{id}/checkpoints"): (
        "tests.test_authorization_matrix",
        "test_wp18_landed_checkpoint_routes_enforce_their_callers",
    ),
    # --- Submission row (Agent / Owner)
    ("POST", "/api/v1/tasks/{id}/resolution"): (
        "tests.test_authorization_matrix",
        "test_wp32_landed_resolution_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/tasks/{id}/resolutions"): (
        "tests.test_authorization_matrix",
        "test_wp32_landed_resolution_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/resolutions/{id}/patch"): (
        "tests.test_authorization_matrix",
        "test_wp32_landed_resolution_routes_enforce_their_callers",
    ),
    # --- Audit row (Auditor / Owner)
    ("POST", "/api/v1/tasks/{id}/audit-verdict"): (
        "tests.test_authorization_matrix",
        "test_wp33_landed_audit_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/tasks/{id}/audit-reports"): (
        "tests.test_authorization_matrix",
        "test_wp33_landed_audit_routes_enforce_their_callers",
    ),
    # --- Review row (Owner; §12.2 adds Device) — WP-3.6's landing case
    # (the deferred entry it replaced); the whole printed grid for the
    # row also runs in the PROBES walk above.
    ("POST", "/api/v1/tasks/{id}/review"): (
        "tests.test_authorization_matrix",
        "test_wp36_landed_review_route_enforces_its_callers",
    ),
    # --- Attachments row (Owner / Agent (read)) — the WP-1.11/1.13/1.14
    # landing cases in the adopted matrix; the negative token paths on these
    # same five routes live in this package's test_attachment_access_paths.
    ("POST", "/api/v1/tasks/{id}/attachments"): (
        "tests.test_authorization_matrix",
        "test_wp111_landed_attachment_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/tasks/{id}/attachments"): (
        "tests.test_authorization_matrix",
        "test_wp111_landed_attachment_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/attachments/{id}"): (
        "tests.test_authorization_matrix",
        "test_wp111_landed_attachment_routes_enforce_their_callers",
    ),
    ("GET", "/api/v1/attachments/{id}/content"): (
        "tests.test_authorization_matrix",
        "test_wp114_landed_content_route_enforces_its_callers",
    ),
    ("DELETE", "/api/v1/attachments/{id}"): (
        "tests.test_authorization_matrix",
        "test_wp111_landed_attachment_routes_enforce_their_callers",
    ),
    # --- Sessions row (Bridge; the bridge presents a project agent token)
    ("POST", "/api/v1/agent-sessions"): (
        "tests.test_authorization_matrix",
        "test_wp16_landed_routes_enforce_their_callers",
    ),
    ("POST", "/api/v1/agent-sessions/{id}/end"): (
        "tests.test_authorization_matrix",
        "test_wp16_landed_routes_enforce_their_callers",
    ),
    # --- Events row (Owner; Section 9.6: agents never subscribe)
    ("GET", "/api/v1/events"): (
        "tests.events.test_event_authorization",
        "test_history_denies_what_the_stream_denies",
    ),
    ("GET", "/api/v1/events/stream"): (
        "tests.events.test_event_authorization",
        "test_owner_and_device_hold_the_stream",
    ),
    # --- Dashboard row (Owner)
    ("GET", "/api/v1/dashboard/summary"): (
        "tests.test_dashboard_summary",
        "test_every_agent_role_is_refused_with_role_not_permitted",
    ),
    # --- Ops row (Infrastructure; no authentication)
    ("GET", "/health/live"): (
        "tests.test_health",
        "test_live_returns_success_without_dependency_checks",
    ),
    ("GET", "/health/ready"): (
        "tests.test_health",
        "test_ready_returns_success_when_database_and_cache_are_reachable",
    ),
    # --- documented plan gap (see GAPS)
    ("GET", "/api/v1/devices"): ("tests.test_device_list", "test_list_requires_an_owner_session"),
}

_METHODS = frozenset({"get", "put", "post", "delete", "patch"})
_TOKEN = re.compile(r"(GET|POST|PATCH|DELETE)(?:/(GET|POST|PATCH|DELETE))?\s+`(/[^`]+)`")


class _Row(NamedTuple):
    """One Section 9.2 row: area, operation, caller column (plan verbatim)."""

    area: str
    method: str
    path: str  # /api/v1-prefixed template; the one documented query suffix stripped
    caller: str


def _plan_section_9_2() -> str:
    text = PLAN_PATH.read_text(encoding="utf-8")
    assert "### 9.2 REST API surface" in text, "the plan lost Section 9.2"
    return text.split("### 9.2 REST API surface", 1)[1].split("### 9.3", 1)[0]


def _section_9_2_rows() -> list[_Row]:
    """Parse the plan's endpoint table: Area | Endpoint (method path) | Caller."""
    rows: list[_Row] = []
    for line in _plan_section_9_2().splitlines():
        if not line.startswith("|") or line.startswith("| Area |") or line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 3, f"unexpected Section 9.2 table shape: {line!r}"
        area, endpoints, caller = cells
        area_rows: list[_Row] = []
        for match in _TOKEN.finditer(endpoints):
            methods = [match.group(1)] + ([match.group(2)] if match.group(2) else [])
            # The one documented query suffix (pagination.md's content
            # exception) rides along in the plan text; the row key is the
            # path only — the schema and the URLConf carry no query string.
            path = match.group(3).split("?", 1)[0]
            for method in methods:
                area_rows.append(_Row(area=area, method=method, path=_prefix(path), caller=caller))
        backticked = {p.split("?", 1)[0] for p in re.findall(r"`(/[^`]+)`", endpoints)}
        assert {row.path.removeprefix("/api/v1") for row in area_rows} == backticked, (
            f"Section 9.2 area {area!r} has a backticked path the token regex missed"
        )
        rows.extend(area_rows)
    return rows


def _prefix(path: str) -> str:
    """Section 9.2 paths print without the base path; Ops stays at the root."""
    return path if path.startswith("/health/") else f"/api/v1{path}"


def _norm(path: str) -> str:
    """Collapse every ``{placeholder}`` so template spellings compare equal."""
    return re.sub(r"\{[^}]+\}", "{}", path)


def _sample(path: str) -> str:
    """A concrete path for ``resolve()``/deferred membership per URLConf converters."""
    sample = path.replace("{pid}", "PID00001")
    if sample.startswith("/api/v1/tasks/"):
        # The adopted deferred entries address tasks by the bare integer the
        # <str:id> converter also accepts; real rows use canonical task ids.
        deferred_shape = sample.endswith(("/transition", "/review"))
        sample = sample.replace("{id}", "1" if deferred_shape else "PID00001-T001")
    elif sample.startswith("/api/v1/resolutions/"):
        sample = sample.replace("{id}", "00000000-0000-4000-8000-000000000001")
    else:
        sample = sample.replace("{id}", "1").replace("{task}", "1")
    return sample


def _matches_template(entry: str, template: str) -> bool:
    """Does the concrete deferred entry address this row's template?"""
    given, row = entry.split("/"), template.split("/")
    if len(given) != len(row):
        return False
    return all(
        g.startswith("{") and g.endswith("}") or g == k for g, k in zip(row, given, strict=False)
    )


def _actors_for_caller(caller: str) -> frozenset[str]:
    """The plan's caller column mapped onto the adopted matrix's actor kinds."""
    agents = frozenset(adopted.AGENT_ROLES)
    table: dict[str, frozenset[str]] = {
        "Owner": frozenset({"owner"}),
        "Owner; agents read-only for own project": agents | {"owner"},
        "Agent": agents,
        "Agent / Owner": agents | {"owner"},
        "Auditor / Owner": frozenset({"auditor", "owner"}),
        "Merge Executor": frozenset({"merge_executor"}),
        "Owner / Agent (read)": agents | {"owner"},
        "Bridge": agents,  # the bridge presents a project-scoped agent token
        "Mobile": frozenset({"device"}),
        "Infrastructure": frozenset({"anonymous"}),
    }
    assert caller in table, f"Section 9.2 grew an unmapped caller column: {caller!r}"
    return table[caller]


@pytest.fixture(scope="module")
def plan_rows() -> list[_Row]:
    return _section_9_2_rows()


@pytest.fixture(scope="module")
def openapi_operations() -> list[tuple[str, str]]:
    generated = cast(
        dict[str, Any],
        SchemaGenerator().get_schema(request=None, public=True),  # type: ignore[no-untyped-call]
    )
    assert generated is not None, "schema generation produced no document"
    operations: list[tuple[str, str]] = []
    for path, item in generated["paths"].items():
        if not isinstance(item, dict):
            continue
        for method in item:
            if method in _METHODS:
                operations.append((method.upper(), path))
    return operations


# --- the enumeration contract ----------------------------------------------


def test_section_9_2_table_parses_to_the_expected_surface(plan_rows: list[_Row]) -> None:
    """The plan table transcribes exactly; unknown shapes fail loudly here."""
    assert len(plan_rows) == 46, "Section 9.2's endpoint table changed — re-read the plan"
    keys = {(row.method, row.path) for row in plan_rows}
    assert keys == (set(PROOF) - GAPS) | DEFERRED_ROWS, "PROOF/DEFERRED_ROWS drifted from the plan"
    for row in plan_rows:
        _actors_for_caller(row.caller)  # assertion inside: unmapped caller column


def test_caller_cells_map_onto_the_adopted_matrix_actor_kinds(
    plan_rows: list[_Row],
) -> None:
    """Endpoint × roles: every mapped cell stays inside the Section 12.2 grid."""
    known = set(adopted.ACTORS)
    for row in plan_rows:
        actors = _actors_for_caller(row.caller)
        assert actors, f"{row.area} row grants no actor"
        assert actors <= known, (row.area, actors - known)


def test_generated_openapi_operations_all_carry_a_row(
    openapi_operations: list[tuple[str, str]], plan_rows: list[_Row]
) -> None:
    """The MT risk note made executable: a new endpoint without a row fails."""
    enumerated_by_path: dict[str, set[str]] = {}
    for row in plan_rows:
        enumerated_by_path.setdefault(_norm(row.path), set()).add(row.method)
    gap_keys = {(method, _norm(path)) for method, path in GAPS}
    for method, path in openapi_operations:
        if (method, _norm(path)) in gap_keys:
            continue  # documented plan gap — its case is the PROOF pointer
        methods = enumerated_by_path.get(_norm(path))
        assert methods is not None, (
            f"{method} {path} is served but prints no Section 9.2 row — add the row to the "
            "plan (owner decision) and to this suite's PROOF, or document it in GAPS"
        )
        assert method in methods, f"{method} {path} has no Section 9.2 method match in {methods}"
    # GAPS entries must still be genuinely unplanned: once the plan prints the
    # row, the gap entry must be deleted (no stale allowances accumulate).
    planned = {(row.method, _norm(row.path)) for row in plan_rows}
    for method, path in GAPS:
        assert (method, _norm(path)) not in planned, f"stale GAPS entry: {(method, path)}"


def test_every_row_resolves_or_is_deferred_in_the_adopted_guard(
    plan_rows: list[_Row],
) -> None:
    """A row is either live in the URLConf or a named deferred entry — never both."""
    for row in plan_rows:
        sample = _sample(row.path)
        if (row.method, row.path) in DEFERRED_ROWS:
            assert sample in adopted.DEFERRED_ENDPOINTS, (
                f"{row.method} {row.path} is marked deferred here but {sample!r} is not in the "
                "adopted matrix's DEFERRED_ENDPOINTS — the two guards must agree"
            )
            with pytest.raises(Resolver404):
                resolve(sample)
            continue
        try:
            resolve(sample)
        except Resolver404:
            raise AssertionError(
                f"{row.method} {row.path} stopped resolving ({sample}) — update this suite "
                "(the adopted drift guard only tracks DEFERRED_ENDPOINTS)"
            ) from None


def test_deferred_entries_map_back_onto_exactly_one_row(plan_rows: list[_Row]) -> None:
    """The reverse direction: the adopted guard defers nothing unenumerated."""
    for entry in adopted.DEFERRED_ENDPOINTS:
        matches = [row for row in plan_rows if _matches_template(entry, row.path)]
        assert len(matches) == 1, f"{entry} matches {len(matches)} Section 9.2 rows"
        row = matches[0]
        assert (row.method, row.path) in DEFERRED_ROWS, (
            f"{entry} is deferred in the adopted matrix but this suite walks "
            f"{row.method} {row.path} as live — flip the row"
        )


def test_every_live_row_links_to_its_behavioral_proof() -> None:
    """Adoption pointer: a missing or renamed proof test fails the suite."""
    for (method, path), (module_name, test_name) in PROOF.items():
        module = importlib.import_module(module_name)
        proof = getattr(module, test_name, None)
        assert callable(proof), f"proof {module_name}.{test_name} for {method} {path} is missing"
        assert test_name.startswith("test_"), (module_name, test_name)
