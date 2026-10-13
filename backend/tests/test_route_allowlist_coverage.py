"""MT-5.2-02 — route-allowlist coverage (Sections 15.2, 9.2, 20.5).

Parses the machine-readable rule block in
``infra/cloudflare/route-allowlist.md`` (the first JSON fence under §7) and
asserts, without any network or Cloudflare state, that:

* every Section 15.2 row appears **exactly once** with the plan's own row
  text and exposure text, and carries explicit path rules (traceability —
  one-to-one table-to-rule mapping, Section 20.5);
* the default for the tunnel hostname is **deny** — rows not marked ``Yes``
  are never ``allow``, and every Section 9.2 path has an explicit decision
  (no implicit allowances);
* LAN-only rows (tokens/policy/admin) and Health are denied and flagged
  LAN-unaffected (Section 19 WP-5.2 acceptance — the LAN half itself runs
  in ``e2e/route_verify.py`` / the checklist);
* conditional rows require a service token exactly as Section 15.2 says and
  are denied in the v1 (remote-agents-off) posture;
* the OQ-12 decision on task create/publish is recorded, not silently
  defaulted;
* ``infra/cloudflare/ingress.yaml`` agrees rule for rule: each allow path's
  first matching ingress rule routes to the backend, each deny path's
  matches a ``http_status:403`` rule (the MT's prefix-divergence risk —
  deny rules must come *before* the ``^/api/`` rule), and no deny rule ever
  catches an allowed path;
* the edge mechanisms referenced by the rules exist in
  ``infra/cloudflare/access-policy.md`` (deny applications A1-A10), and the
  four method-shared writes point at the W1-W4 method rules of §4;
* no secret or concrete hostname is committed (Section 20.4 item 3).

Run: ``pytest backend/tests/test_route_allowlist_coverage.py -v``
(live blocked-vs-allowed execution is MT-5.2-04's checklist).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_MD = REPO_ROOT / "infra" / "cloudflare" / "route-allowlist.md"
INGRESS_YAML = REPO_ROOT / "infra" / "cloudflare" / "ingress.yaml"
ACCESS_POLICY_MD = REPO_ROOT / "infra" / "cloudflare" / "access-policy.md"

#: The Section 15.2 table, verbatim — the plan is the single source of truth,
#: so the row texts live here as literals rather than being derived from the
#: document under test (a doc typo would otherwise pass itself).
SECTION_15_2_ROWS: tuple[tuple[str, str, str], ...] = (
    ("auth-devices", "Auth, devices", "Yes"),
    (
        "reads-review-dashboard-events",
        "Projects (read), tasks (read), review, dashboard, events stream",
        "Yes",
    ),
    ("task-create-publish", "Task create/publish", "Yes (Could)"),
    (
        "tokens-policy-admin",
        "Agent token creation, policy editing, admin",
        "No (LAN only)",
    ),
    (
        "agent-work",
        "Agent work endpoints (claim, checkpoints, submit)",
        "Only if remote agents are used, with a service token",
    ),
    (
        "merge-queue",
        "Merge queue",
        "Only for a remote Merge Executor, with a service token",
    ),
    ("health", "Health", "Internal only"),
)

ROW_IDS = {row[0] for row in SECTION_15_2_ROWS}

#: Every Section 9.2 path (the plan's endpoint column, placeholder forms) —
#: each must appear in the allowlist with an explicit decision.
SECTION_9_2_PATHS: frozenset[str] = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/logout",
        "/api/v1/auth/refresh",
        "/api/v1/tokens/agent",
        "/api/v1/tokens/{id}",
        "/api/v1/tokens",
        "/api/v1/devices",
        "/api/v1/devices/{id}",
        "/api/v1/projects",
        "/api/v1/projects/{pid}",
        "/api/v1/projects/{pid}/manifest",
        "/api/v1/projects/{pid}/policy",
        "/api/v1/projects/{pid}/tasks",
        "/api/v1/tasks/{id}",
        "/api/v1/tasks/{id}/transition",
        "/api/v1/projects/{pid}/work",
        "/api/v1/tasks/{id}/claim",
        "/api/v1/tasks/{id}/release",
        "/api/v1/tasks/{id}/checkpoints",
        "/api/v1/tasks/{id}/resolution",
        "/api/v1/tasks/{id}/resolutions",
        "/api/v1/resolutions/{id}/patch",
        "/api/v1/tasks/{id}/audit-verdict",
        "/api/v1/tasks/{id}/audit-reports",
        "/api/v1/tasks/{id}/review",
        "/api/v1/merge/pending",
        "/api/v1/merge/{task}/start",
        "/api/v1/merge/{task}/result",
        "/api/v1/tasks/{id}/attachments",
        "/api/v1/attachments/{id}",
        "/api/v1/attachments/{id}/content",
        "/api/v1/agent-sessions",
        "/api/v1/agent-sessions/{id}/end",
        "/api/v1/events/stream",
        "/api/v1/events",
        "/api/v1/dashboard/summary",
        "/health/live",
        "/health/ready",
    }
)


def _extract_json_block(md_path: Path) -> dict[str, Any]:
    """Return the first ```json fence after the machine-readable heading."""
    text = md_path.read_text(encoding="utf-8")
    heading = "## 7. Machine-readable rule table"
    assert heading in text, f"{md_path.name} lost its machine-readable section"
    tail = text.split(heading, 1)[1]
    match = re.search(r"```json\n(.*?)\n```", tail, flags=re.DOTALL)
    assert match, f"{md_path.name} has no JSON block under {heading!r}"
    return cast_json(json.loads(match.group(1)))


def cast_json(payload: object) -> dict[str, Any]:
    assert isinstance(payload, dict), "the rule block is a JSON object"
    return payload


@pytest.fixture(scope="module")
def allowlist() -> dict[str, Any]:
    return _extract_json_block(ALLOWLIST_MD)


@pytest.fixture(scope="module")
def rows(allowlist: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in allowlist["rows"]}


@pytest.fixture(scope="module")
def all_paths(allowlist: dict[str, Any]) -> list[dict[str, Any]]:
    return [path for row in allowlist["rows"] for path in row["paths"]]


def _match_ingress(sample: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    """First ingress rule matching ``sample`` (cloudflared semantics)."""
    hostname = "orchestrator.<owner-domain>"
    for rule in rules:
        if "hostname" in rule and rule["hostname"] != hostname:
            continue
        path_pattern = rule.get("path")
        if path_pattern is not None and not re.search(str(path_pattern), sample):
            continue
        return rule
    raise AssertionError(f"no ingress rule matched {sample!r} (missing catch-all?)")


# --- Section 15.2 rows: one-to-one mapping (Section 20.5) --------------------


def test_every_section_15_2_row_appears_with_its_exact_text(
    allowlist: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> None:
    """The plan's seven rows map one-to-one onto explicit rule groups."""
    assert set(rows) == ROW_IDS | {"unnamed-default-deny"}
    for row_id, plan_row, plan_exposed in SECTION_15_2_ROWS:
        row = rows[row_id]
        assert row["plan_row"] == plan_row, row_id
        assert row["plan_exposed"] == plan_exposed, row_id
        assert row["paths"], f"{row_id} has no explicit path rules"


def test_section_9_2_paths_all_carry_an_explicit_decision(all_paths: list[dict[str, Any]]) -> None:
    """No Section 9.2 endpoint is missing from the allowlist (both ways)."""
    covered = {entry["path"] for entry in all_paths}
    missing = SECTION_9_2_PATHS - covered
    assert not missing, f"Section 9.2 paths without a rule: {sorted(missing)}"


def test_every_path_back_references_a_known_row(
    allowlist: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> None:
    for row in allowlist["rows"]:
        for entry in row["paths"]:
            assert entry.get("row", row["id"]) in rows
            assert entry["decision"] in {"allow", "deny", "conditional-deny"}
            assert entry["edge"] in {"access-root", "access-block", "method-rule"}


# --- default deny (Section 15.2; MT-5.2-02 scope) ---------------------------


def test_default_for_the_tunnel_hostname_is_deny(
    allowlist: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> None:
    assert allowlist["meta"]["default_decision"] == "deny"
    for row_id, _, plan_exposed in SECTION_15_2_ROWS:
        decision = rows[row_id]["decision"]
        if plan_exposed == "Yes":
            assert decision == "allow", row_id
        else:
            assert decision != "allow", f"{row_id} must not be blanket-allowed"


def test_lan_only_and_health_rows_are_denied_and_flagged(rows: dict[str, dict[str, Any]]) -> None:
    """Section 19 WP-5.2 acceptance, config half: denied at the edge here,
    LAN reachability proven by the checklist/e2e run (documented split)."""
    for row_id in ("tokens-policy-admin", "health"):
        row = rows[row_id]
        assert row["decision"] == "deny"
        assert all(entry["decision"] == "deny" for entry in row["paths"])
    assert rows["tokens-policy-admin"].get("lan_unaffected") is True


def test_conditional_rows_require_a_service_token_and_are_denied_in_v1(
    allowlist: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> None:
    meta = allowlist["meta"]
    assert meta["remote_agents_enabled"] is False
    assert meta["remote_merge_executor_enabled"] is False
    for row_id in ("agent-work", "merge-queue"):
        row = rows[row_id]
        assert row["requires_service_token"] is True, row_id
        assert row["decision"] == "conditional-deny"
        assert all(entry["edge"] == "access-block" for entry in row["paths"])
        assert all(entry["ingress"] == "deny-403" for entry in row["paths"])


def test_oq12_task_create_decision_is_recorded_not_silently_defaulted(
    allowlist: dict[str, Any], rows: dict[str, dict[str, Any]]
) -> None:
    row = rows["task-create-publish"]
    assert row["plan_exposed"] == "Yes (Could)"
    assert row["decision"] == "deny", "OQ-12 keeps creation out of v1"
    assert "No (Could)" in row["oq12"]
    assert allowlist["meta"]["oq12_task_create_in_v1"] is False
    assert "review and monitoring only" in allowlist["meta"]["oq12_resolution"]
    assert all(entry["decision"] == "deny" for entry in row["paths"])


def test_unnamed_paths_are_flagged_not_silently_allowed(rows: dict[str, dict[str, Any]]) -> None:
    unnamed = rows["unnamed-default-deny"]
    assert unnamed["decision"] == "deny"
    for entry in unnamed["paths"]:
        assert entry["flagged"], entry["path"]
        assert entry["decision"] == "deny"


# --- ingress.yaml agreement (the prefix-divergence guard) -------------------


@pytest.fixture(scope="module")
def ingress_rules() -> list[dict[str, Any]]:
    loaded = yaml.safe_load(INGRESS_YAML.read_text(encoding="utf-8"))
    rules = loaded["ingress"]
    assert isinstance(rules, list) and rules
    return rules


def test_ingress_deny_rules_come_before_the_api_rule(ingress_rules: list[dict[str, Any]]) -> None:
    api_index = next(i for i, r in enumerate(ingress_rules) if r.get("path") == "^/api/")
    deny_indexes = [i for i, r in enumerate(ingress_rules) if r.get("service") == "http_status:403"]
    assert deny_indexes, "WP-5.2 deny rules missing from ingress.yaml"
    assert max(deny_indexes) < api_index, "a deny rule is shadowed by ^/api/"


def test_ingress_matches_every_allowlist_decision(
    all_paths: list[dict[str, Any]], ingress_rules: list[dict[str, Any]]
) -> None:
    """Rule-for-rule proof: allow → backend, deny-403 → 403, method-split
    rides ^/api/ (edge W1-W4 does the denying — Section 15.2 default)."""
    for entry in all_paths:
        matched = _match_ingress(entry["sample"], ingress_rules)
        service = str(matched.get("service"))
        if entry["ingress"] == "backend":
            assert service == "http://backend:8000", (
                f"{entry['sample']} must route to backend, matched {matched}"
            )
        elif entry["ingress"] == "deny-403":
            assert service == "http_status:403", (
                f"{entry['sample']} must hit a 403 deny rule, matched {matched}"
            )
        else:  # pragma: no cover - guarded by the doc assertions below
            raise AssertionError(f"unknown ingress expectation: {entry['ingress']}")


def test_no_deny_rule_catches_an_allowed_path(
    all_paths: list[dict[str, Any]], ingress_rules: list[dict[str, Any]]
) -> None:
    """The risk-note case: /api/v1/tokens/agent-style rules must never
    swallow an exposed row's path."""
    for entry in all_paths:
        if entry["decision"] != "allow":
            continue
        matched = _match_ingress(entry["sample"], ingress_rules)
        assert matched.get("service") != "http_status:403", (
            f"deny rule shadowed the allowed path {entry['sample']}"
        )


def test_catch_all_rule_is_last_and_404(ingress_rules: list[dict[str, Any]]) -> None:
    last = ingress_rules[-1]
    assert last.get("service") == "http_status:404"
    assert "hostname" not in last and "path" not in last


# --- edge mechanisms referenced by the rules exist --------------------------


def test_every_referenced_access_application_is_defined(all_paths: list[dict[str, Any]]) -> None:
    policy = ACCESS_POLICY_MD.read_text(encoding="utf-8")
    referenced = {entry["app"] for entry in all_paths if entry.get("app")}
    assert referenced, "deny paths must name their Access application"
    for app_id in referenced:
        assert re.search(rf"\b{app_id}\b", policy), (
            f"{app_id} referenced by the allowlist but absent from access-policy.md"
        )


def test_method_split_writes_point_at_w1_to_w4(all_paths: list[dict[str, Any]]) -> None:
    """The four path-shared writes are denied by method rules (§4), each
    flagged with its rule id — and the allowlist documents all four."""
    method_rules = [e for e in all_paths if e["edge"] == "method-rule"]
    markers = set()
    for entry in method_rules:
        assert entry["flagged"], entry["path"]
        found = re.findall(r"\bW[1-4]\b", entry["flagged"])
        assert found, f"{entry['path']} lacks its W-rule reference"
        markers.update(found)
    assert len(method_rules) == 4, "Section 9.2 has exactly four path-shared writes"
    assert markers == {"W1", "W2", "W3", "W4"}
    allowlist_text = ALLOWLIST_MD.read_text(encoding="utf-8")
    assert "## 4. Method-aware rules" in allowlist_text
    for marker in sorted(markers):
        assert marker in allowlist_text


# --- Section 20.4 item 3: no secrets, no environment-specific hostname ------


def test_no_secret_or_concrete_hostname_is_committed() -> None:
    for path in (ALLOWLIST_MD, INGRESS_YAML, ACCESS_POLICY_MD):
        text = path.read_text(encoding="utf-8")
        concrete = re.search(r"orchestrator\.(?!<owner-domain>)[a-z0-9.-]+\.[a-z]{2,}", text)
        assert concrete is None, f"concrete hostname in {path.name}: {concrete}"
        assert not re.search(r"(?:tunnel|cf|service)[_-]?token.*[A-Za-z0-9]{24,}", text, re.I), (
            f"possible committed token in {path.name}"
        )
