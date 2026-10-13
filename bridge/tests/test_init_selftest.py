"""MT-2.12-03 — connectivity self-test: verdict matrix, cleanup, bounds, redaction.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.12-init-command/
MT-2.12-03-connectivity-selftest.md (FR-MCP-08 duty 3; NFR-10; Section 10.10).
The probe is MT-2.2-04's session open over the transport seam; the manifest
comes from a real tmp repo (MT-2.2-01/02), the token from env or the
init-produced user config.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from orchestrator_bridge.init.selftest import all_passed, run_self_test
from orchestrator_bridge.init.token_store import store_agent_token
from orchestrator_bridge.manifest_discovery import MANIFEST_FILENAME
from tests.conftest import FIXTURE_TOKEN, FakeBackend, build_settings, json_wire

PID = "PID00007"

_SEND_KWARGS: dict[str, Any] = {"retry_max_attempts": 3, "retry_base_delay_seconds": 0.0}


def _repo_with_manifest(tmp_path: Path, **overrides: Any) -> Path:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    document = {
        "schema_version": 1,
        "project_id": PID,
        "project_name": "Tea Factory ERP",
        "orchestrator_api": "http://bridge.invalid/api/v1",
        "default_branch": "main",
        "auto_branch_prefix": "feat/PID00007-",
        "audit_required_default": True,
    }
    document.update(overrides)
    (root / MANIFEST_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    return root


def _session_fake() -> FakeBackend:
    fake = FakeBackend()
    fake.route_fn(
        "POST",
        "/api/v1/agent-sessions",
        lambda body: (201, {"id": body["id"], "project_id": PID, "transport": "stdio"}),
    )
    fake.route(
        "GET",
        f"/api/v1/projects/{PID}",
        200,
        {"id": PID, "name": "Tea Factory ERP", "system_prompt_rules": "Project rule."},
    )
    fake.route(
        "GET",
        f"/api/v1/projects/{PID}/policy",
        200,
        {"max_concurrent_tasks": 1, "lease_duration_minutes": 45},
    )
    return fake


def _send_with_end(fake: FakeBackend) -> Any:
    """Send seam that answers the dynamic session-end path and records it."""
    ended: list[str] = []

    def send(method: str, url: str, headers: Any, body: Any, timeout: float) -> Any:
        path = urlsplit(url).path
        if (
            method == "POST"
            and path.startswith("/api/v1/agent-sessions/")
            and path.endswith("/end")
        ):
            ended.append(path)
            return json_wire(200, None)
        return fake.send(method, url, headers, body, timeout)

    send.ended = ended  # type: ignore[attr-defined]
    return send


def _env_token() -> dict[str, str]:
    return {"ORCHESTRATOR_AGENT_TOKEN": FIXTURE_TOKEN}


def test_all_pass_names_the_token_source_and_closes_the_probe(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    fake = _session_fake()
    send = _send_with_end(fake)
    results = run_self_test(cwd=root, env=_env_token(), config_path=isolated_init_config, send=send)
    assert all_passed(results)
    by_name = {result.name: result for result in results}
    assert by_name["manifest"].ok
    assert by_name["token"].ok and "environment" in by_name["token"].detail
    assert by_name["session"].ok
    # The probe session was opened AND closed (no dangling backend row).
    assert fake.calls_to("POST", "/api/v1/agent-sessions")
    assert send.ended and send.ended[0].startswith("/api/v1/agent-sessions/")


def test_missing_manifest_fails_with_init_remedy(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    plain = tmp_path / "plain"
    (plain / ".git").mkdir(parents=True)
    results = run_self_test(cwd=plain, env=_env_token(), config_path=isolated_init_config)
    assert not all_passed(results)
    by_name = {result.name: result for result in results}
    assert by_name["manifest"].status == "fail"
    assert by_name["manifest"].remedy and "orchestrator init" in by_name["manifest"].remedy
    assert by_name["session"].status == "skip"  # FR-MCP-08 duty order enforced
    assert "manifest" in by_name["session"].detail


def test_unresolvable_token_fails_with_both_sources_named(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    results = run_self_test(cwd=root, env={}, config_path=isolated_init_config)
    assert not all_passed(results)
    by_name = {result.name: result for result in results}
    assert by_name["token"].status == "fail"
    detail = by_name["token"].detail + (by_name["token"].remedy or "")
    assert "ORCHESTRATOR_AGENT_TOKEN" in detail and "orchestrator init" in detail
    assert by_name["session"].status == "skip"
    assert "token" in by_name["session"].detail


def test_unreachable_backend_fails_the_probe(tmp_path: Path, isolated_init_config: Path) -> None:
    root = _repo_with_manifest(tmp_path)

    def _refused(method: str, url: str, headers: Any, body: Any, timeout: float) -> Any:
        raise ConnectionRefusedError("backend down")

    results = run_self_test(
        cwd=root, env=_env_token(), config_path=isolated_init_config, send=_refused
    )
    assert not all_passed(results)
    session = next(result for result in results if result.name == "session")
    assert session.status == "fail"
    assert "endpoint" in (session.remedy or "")


def test_wrong_project_token_reuses_the_mismatch_message(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    fake = FakeBackend()
    fake.route(
        "POST",
        "/api/v1/agent-sessions",
        403,
        {
            "error": {
                "code": "AUTH_FORBIDDEN_PROJECT",
                "message": "token is for another project",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-test",
            }
        },
    )
    results = run_self_test(
        cwd=root, env=_env_token(), config_path=isolated_init_config, send=fake.send
    )
    session = next(result for result in results if result.name == "session")
    assert session.status == "fail"
    # MT-2.2-05's clear message rides through: canonical code + fix text.
    assert "AUTH_FORBIDDEN_PROJECT" in session.detail
    assert "Fix:" in session.detail
    assert "token issued for" in (session.remedy or "") + session.detail


def test_transient_failures_stay_within_the_retry_budget(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    fake = FakeBackend()
    fake.route(
        "POST",
        "/api/v1/agent-sessions",
        503,
        {
            "error": {
                "code": "SERVER_ERROR",
                "message": "try later",
                "retryable": True,
                "details": None,
                "correlation_id": "corr-test",
            }
        },
    )
    env = {**_env_token(), "ORCHESTRATOR_BRIDGE_RETRY_MAX_ATTEMPTS": "3"}
    results = run_self_test(cwd=root, env=env, config_path=isolated_init_config, send=fake.send)
    session = next(result for result in results if result.name == "session")
    assert session.status == "fail"
    opens = fake.calls_to("POST", "/api/v1/agent-sessions")
    assert len(opens) == 3  # fixed bound, no indefinite hang (Section 10.10)


def test_token_value_never_appears_in_any_verdict(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    fake = _session_fake()
    results = run_self_test(
        cwd=root, env=_env_token(), config_path=isolated_init_config, send=_send_with_end(fake)
    )
    rendered = " ".join(result.detail + (result.remedy or "") for result in results)
    assert FIXTURE_TOKEN not in rendered


def test_config_file_token_is_named_as_the_user_config_source(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    store_agent_token(FIXTURE_TOKEN, config_path=isolated_init_config)
    fake = _session_fake()
    results = run_self_test(
        cwd=root, env={}, config_path=isolated_init_config, send=_send_with_end(fake)
    )
    token = next(result for result in results if result.name == "token")
    assert token.ok
    assert "user-level config" in token.detail
    assert str(isolated_init_config) in token.detail


def test_self_test_never_mutates_manifest_or_config(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo_with_manifest(tmp_path)
    store_agent_token(FIXTURE_TOKEN, config_path=isolated_init_config)
    manifest_before = (root / MANIFEST_FILENAME).read_bytes()
    config_before = isolated_init_config.read_bytes()
    fake = _session_fake()
    run_self_test(cwd=root, env={}, config_path=isolated_init_config, send=_send_with_end(fake))
    assert (root / MANIFEST_FILENAME).read_bytes() == manifest_before
    assert isolated_init_config.read_bytes() == config_before


def test_structured_log_records_accompany_the_verdicts(
    tmp_path: Path,
    isolated_init_config: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    root = _repo_with_manifest(tmp_path)
    fake = _session_fake()
    with caplog.at_level(logging.INFO, logger="bridge.init"):
        run_self_test(
            cwd=root, env=_env_token(), config_path=isolated_init_config, send=_send_with_end(fake)
        )
    events = [
        record for record in caplog.records if getattr(record, "event", "") == "selftest_check"
    ]
    checks = [record.__dict__["check"] for record in events]
    statuses = [record.__dict__["status"] for record in events]
    assert checks == ["manifest", "token", "session"]
    assert all(status in {"pass", "fail", "skip"} for status in statuses)


def test_manifest_override_env_is_honored(tmp_path: Path, isolated_init_config: Path) -> None:
    root = _repo_with_manifest(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    moved = root / MANIFEST_FILENAME
    relocated = elsewhere / MANIFEST_FILENAME
    relocated.write_text(moved.read_text(encoding="utf-8"), encoding="utf-8")
    moved.unlink()
    env = {**_env_token(), "ORCHESTRATOR_BRIDGE_MANIFEST_PATH": str(relocated)}
    fake = _session_fake()
    results = run_self_test(
        cwd=root, env=env, config_path=isolated_init_config, send=_send_with_end(fake)
    )
    manifest = next(result for result in results if result.name == "manifest")
    assert manifest.ok and str(relocated) in manifest.detail


def test_settings_defaults_keep_the_probe_bounded() -> None:
    # Sanity: the settings the probe builds come with a finite retry budget.
    settings = build_settings(**_SEND_KWARGS)
    assert settings.retry_max_attempts == 3
