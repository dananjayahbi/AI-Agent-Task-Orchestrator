"""MT-5.2-04 — route-verification checklist coverage (Sections 15.2, 18, 20.5).

Parses the machine-readable checklist block in
``infra/cloudflare/route-verification-checklist.md`` (§6) and asserts:

* every Section 15.2 row appears with its plan text, concrete endpoint
  samples, and **both** vantage points spelled out per check — no blank
  expectations (MT-5.2-04 acceptance; Section 20.5 traceability);
* the checklist and ``route-allowlist.md`` stay in lockstep: same
  (sample, methods) pairs, expectations derived from the same decisions —
  an allowlist edit without a checklist edit fails here, which is the
  anti-drift half of the re-run rule;
* the Section 19 WP-5.2 acceptance is directly executable: blocked rows
  expect an edge denial on the public vantage *and* an application response
  on the LAN vantage, cell by cell;
* the Section 15.3 layers are represented: Access-gate hooks V1-V5 (layer
  1), the ingress structural hook, and the rate-limit hooks R-API /
  R-API-TUNNEL / R-EDGE (layer 4);
* the results template and the re-run instruction exist (Section 20.4
  item 1), and the expectation vocabulary covers every value the checks use.

Run: ``pytest backend/tests/test_route_checklist_coverage.py -v``.
Live execution of the matrix is the checklist's own job (``e2e/route_verify.py``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKLIST_MD = REPO_ROOT / "infra" / "cloudflare" / "route-verification-checklist.md"
ALLOWLIST_MD = REPO_ROOT / "infra" / "cloudflare" / "route-allowlist.md"
ACCESS_POLICY_MD = REPO_ROOT / "infra" / "cloudflare" / "access-policy.md"

CHECKLIST_HEADING = "## 6. Machine-readable checklist"
ALLOWLIST_HEADING = "## 7. Machine-readable rule table"

#: The Section 15.2 rows verbatim (same literals as
#: test_route_allowlist_coverage.py — the plan, not the docs, is the source).
SECTION_15_2_ROWS: tuple[tuple[str, str], ...] = (
    ("auth-devices", "Auth, devices"),
    (
        "reads-review-dashboard-events",
        "Projects (read), tasks (read), review, dashboard, events stream",
    ),
    ("task-create-publish", "Task create/publish"),
    ("tokens-policy-admin", "Agent token creation, policy editing, admin"),
    ("agent-work", "Agent work endpoints (claim, checkpoints, submit)"),
    ("merge-queue", "Merge queue"),
    ("health", "Health"),
)

EXPECTED_VOCABULARY = {
    "app-response",
    "app-response:RATE_LIMITED",
    "edge-gate",
    "edge-block",
    "edge-rate-limit",
    "connection-error",
}

LAYER_CHECK_IDS = {"V1", "V2", "V3", "V4", "V5", "INGRESS", "R-API", "R-API-TUNNEL", "R-EDGE"}


def _json_block_after(md_path: Path, heading: str) -> dict[str, Any]:
    text = md_path.read_text(encoding="utf-8")
    assert heading in text, f"{md_path.name} lost its machine-readable section"
    tail = text.split(heading, 1)[1]
    match = re.search(r"```json\n(.*?)\n```", tail, flags=re.DOTALL)
    assert match, f"{md_path.name} has no JSON block under {heading!r}"
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


def _checklist() -> dict[str, Any]:
    return _json_block_after(CHECKLIST_MD, CHECKLIST_HEADING)


def _allowlist() -> dict[str, Any]:
    return _json_block_after(ALLOWLIST_MD, ALLOWLIST_HEADING)


def _pairs(rows: list[dict[str, Any]]) -> dict[tuple[str, frozenset[str]], dict[str, Any]]:
    """(sample, methods) -> entry/check, over every row of either document."""
    paired: dict[tuple[str, frozenset[str]], dict[str, Any]] = {}
    for row in rows:
        key_rows = "checks" if "checks" in row else "paths"
        for entry in row[key_rows]:
            key = (entry["sample"], frozenset(entry["methods"]))
            assert key not in paired, f"duplicate check pair {key}"
            paired[key] = entry
    return paired


# --- Section 15.2 rows, both vantage points, no blanks ----------------------


def test_every_section_15_2_row_is_present_with_plan_text() -> None:
    checklist = _checklist()
    rows = {row["id"]: row for row in checklist["rows"]}
    for row_id, plan_row in SECTION_15_2_ROWS:
        assert row_id in rows, f"Section 15.2 row {row_id} missing from the checklist"
        assert rows[row_id]["plan_row"] == plan_row, row_id
        assert rows[row_id]["checks"], f"{row_id} has no concrete endpoint checks"


def test_every_check_has_both_vantage_expectations_and_a_sample() -> None:
    checklist = _checklist()
    for row in checklist["rows"]:
        for check in row["checks"]:
            label = f"{row['id']} {check['sample']}"
            assert check["sample"].startswith("/"), label
            assert check["methods"], label
            for field in ("public_no_credentials", "public_with_service_token", "lan"):
                assert check.get(field), f"{label}: blank expectation in {field}"
                assert check[field] in EXPECTED_VOCABULARY, (
                    f"{label}: {field}={check[field]!r} outside the vocabulary"
                )


def test_vocabulary_declares_every_value_the_checks_use() -> None:
    checklist = _checklist()
    assert set(checklist["meta"]["vocabulary"]) == EXPECTED_VOCABULARY
    assert checklist["meta"]["re_run"], "re-run instruction must be recorded (20.4 item 1)"
    text = CHECKLIST_MD.read_text(encoding="utf-8")
    assert "Results template" in text and "Recorded run" in text


# --- checklist and allowlist stay in lockstep -------------------------------


def test_checklist_covers_exactly_the_allowlist_pairs() -> None:
    checklist_pairs = _pairs(_checklist()["rows"])
    allowlist_pairs = _pairs(_allowlist()["rows"])
    missing = set(allowlist_pairs) - set(checklist_pairs)
    extra = set(checklist_pairs) - set(allowlist_pairs)
    assert not missing, f"allowlist rules with no checklist check: {sorted(missing)}"
    assert not extra, f"checklist checks with no allowlist rule: {sorted(extra)}"


def test_expectations_follow_the_allowlist_decisions() -> None:
    """Allow rows: gate publicly, app on the LAN. Deny rows: edge denial
    publicly (with *and* without the service token — V4), app on the LAN."""
    checklist_pairs = _pairs(_checklist()["rows"])
    allowlist = _allowlist()
    rules = [entry for row in allowlist["rows"] for entry in row["paths"]]
    for rule in rules:
        key = (rule["sample"], frozenset(rule["methods"]))
        check = checklist_pairs[key]
        if rule["decision"] == "allow":
            assert check["public_no_credentials"] == "edge-gate", key
            assert check["public_with_service_token"] == "app-response", key
        else:  # deny and conditional-deny (v1) both block at the edge
            assert check["public_no_credentials"] == "edge-block", key
            assert check["public_with_service_token"] == "edge-block", key
        assert check["lan"] == "app-response", key


def test_section_19_acceptance_rows_are_executable_cell_by_cell() -> None:
    """Blocked rows: denial from the public hostname AND success on LAN —
    every cell present for the rows the acceptance names."""
    rows = {row["id"]: row for row in _checklist()["rows"]}
    blocked = (
        "tokens-policy-admin",
        "health",
        "task-create-publish",
        "agent-work",
        "merge-queue",
    )
    for row_id in blocked:
        for check in rows[row_id]["checks"]:
            assert check["public_no_credentials"] == "edge-block", (
                f"{row_id} {check['sample']} must expect a public denial"
            )
            assert check["lan"] == "app-response", (
                f"{row_id} {check['sample']} must expect success on the LAN"
            )


# --- Section 15.3 layers all represented -----------------------------------


def test_access_gate_ingress_and_rate_limit_hooks_are_all_present() -> None:
    checklist = _checklist()
    layer_ids = {check["id"] for check in checklist["layer_checks"]}
    assert layer_ids == LAYER_CHECK_IDS, layer_ids

    layers = {check["id"]: check for check in checklist["layer_checks"]}
    # Layer 1 — the named hooks of access-policy.md §5, expectations as defined there.
    assert layers["V1"]["expected"] == "edge-gate" and layers["V1"]["sample"] == "/api/v1/projects"
    assert layers["V2"]["expected"] == "edge-block" and layers["V2"]["sample"] == "/api/v1/tokens"
    assert layers["V3"]["expected"] == "app-response"  # edge identity is not authentication
    assert layers["V4"]["expected"] == "edge-block"  # Block beats credentials
    assert layers["V5"]["vantage"] == "lan" and layers["V5"]["expected"] == "app-response"
    # Layer 4 — API and edge rate limits both exercised.
    assert layers["R-API"]["expected"] == "app-response:RATE_LIMITED"
    assert layers["R-EDGE"]["expected"] == "edge-rate-limit"

    # The hooks exist in the policy documents they name.
    assert "## 5. Named verification hooks" in ACCESS_POLICY_MD.read_text(encoding="utf-8")
    assert "## 6. Machine-readable coverage block" in (
        REPO_ROOT / "infra" / "cloudflare" / "rate-limits.md"
    ).read_text(encoding="utf-8")


def test_run_instructions_name_the_script_and_the_ci_test() -> None:
    text = CHECKLIST_MD.read_text(encoding="utf-8")
    assert "e2e/route_verify.py" in text
    assert "test_rate_limits_tunnel.py" in text, "the CI rate-limit proof must be linked"
    assert CHECKLIST_MD.parent.joinpath("..", "..", "e2e", "route_verify.py").resolve().is_file()
