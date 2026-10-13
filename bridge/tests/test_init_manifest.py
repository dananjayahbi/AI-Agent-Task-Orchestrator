"""MT-2.12-01 — init manifest write: root resolution, backend truth, overwrite, secrets.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.12-init-command/
MT-2.12-01-manifest-write.md (FR-MCP-08 duty 1; Sections 10.3, 10.11, 19.3;
20.4 item 3). Covers the writer module plus the ``orchestrator init`` flow
through :func:`orchestrator_bridge.init.cli.run_init` (duties chained, one
backend fake at the transport seam).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from orchestrator_bridge.config import load_settings
from orchestrator_bridge.errors import InitError
from orchestrator_bridge.init import manifest_write as mw
from orchestrator_bridge.init.cli import EXIT_FAILURE, EXIT_OK, build_parser, main, run_init
from orchestrator_bridge.manifest_discovery import MANIFEST_FILENAME, discover_manifest
from orchestrator_bridge.manifest_validation import load_manifest_schema, validate_manifest
from orchestrator_bridge.transport import ApiClient, WireResponse
from tests.conftest import (
    FIXTURE_TOKEN,
    FakeBackend,
    RecordedCall,
    StubHttpBackend,
    build_settings,
    json_wire,
)

PID = "PID00007"

SendSeam = Callable[[str, str, Any, Any, float], WireResponse]


def _inputs(**overrides: Any) -> mw.ProjectInputs:
    base: dict[str, Any] = {
        "project_id": PID,
        "name": "Tea Factory ERP",
        "default_branch": "main",
        "branch_prefix": "feat/{PID}-",
        "audit_required_default": True,
    }
    base.update(overrides)
    return mw.ProjectInputs(**base)


def _fake() -> FakeBackend:
    """The Section 9.2 reads init makes, plus the session-open probe."""
    fake = FakeBackend()
    fake.route(
        "GET",
        f"/api/v1/projects/{PID}",
        200,
        {
            "id": PID,
            "name": "Tea Factory ERP",
            "default_branch": "develop",
            "system_prompt_rules": "Project rule.",
        },
    )
    fake.route(
        "GET",
        f"/api/v1/projects/{PID}/policy",
        200,
        {
            "branch_prefix": "feat/{PID}-",
            "audit_required_default": False,
            "lease_duration_minutes": 45,
        },
    )
    fake.route_fn(
        "POST",
        "/api/v1/agent-sessions",
        lambda body: (201, {"id": body["id"], "project_id": PID, "transport": "stdio"}),
    )
    return fake


def _send_with_dynamic_end(fake: FakeBackend) -> SendSeam:
    """Send seam that also answers the dynamic session-end path."""

    def send(method: str, url: str, headers: Any, body: Any, timeout: float) -> WireResponse:
        path = urlsplit(url).path
        if (
            method == "POST"
            and path.startswith("/api/v1/agent-sessions/")
            and path.endswith("/end")
        ):
            fake.calls.append(
                RecordedCall(method=method, url=url, headers=dict(headers), body=None)
            )
            return json_wire(200, None)
        return fake.send(method, url, headers, body, timeout)

    return send


def _repo(tmp_path: Path, *parts: str) -> Path:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True, exist_ok=True)
    if parts:
        leaf = root.joinpath(*parts)
        leaf.mkdir(parents=True, exist_ok=True)
        return leaf
    return root


# --- writer unit level ---------------------------------------------------------


def test_compose_manifest_matches_the_shared_schema_and_example() -> None:
    document = mw.compose_manifest(_inputs(), orchestrator_api="http://localhost:8000/api/v1")
    validated = validate_manifest(document)
    assert validated["project_id"] == PID
    assert document["$schema"] == mw.MANIFEST_SCHEMA_URL
    assert document["auto_branch_prefix"] == "feat/PID00007-"  # G-09 resolved
    assert document["agent_hints"] == {"test_command_default": "see task", "worktree_mode": False}
    # FR-SEC-04 by allowlist: nothing outside the published schema's keys.
    allowed = set(load_manifest_schema()["properties"])
    assert set(document) <= allowed


def test_branch_prefix_resolution_is_the_backend_rule() -> None:
    assert mw.resolve_branch_prefix("feat/{PID}-", PID) == "feat/PID00007-"
    assert mw.resolve_branch_prefix("fix/", PID) == "fix/"


def test_find_git_root_from_subdirectory(tmp_path: Path) -> None:
    subdir = _repo(tmp_path, "src", "deep")
    assert mw.find_git_root(subdir) == (tmp_path / "repo").resolve()


def test_find_git_root_accepts_a_worktree_pointer_file(tmp_path: Path) -> None:
    root = tmp_path / "worktree"
    root.mkdir()
    (root / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    assert mw.find_git_root(root) == root.resolve()


def test_write_at_root_round_trips_through_discovery_and_validator(tmp_path: Path) -> None:
    subdir = _repo(tmp_path, "src")
    document = mw.compose_manifest(_inputs(), orchestrator_api="http://localhost:8000/api/v1")
    outcome = mw.write_manifest(
        tmp_path / "repo", document, force=False, confirm=lambda _q: pytest.fail("no prompt")
    )
    assert outcome is mw.WriteOutcome.WRITTEN
    path = tmp_path / "repo" / MANIFEST_FILENAME
    assert path.is_file()
    discovered = discover_manifest(subdir)  # the MT-2.2-01 walk finds it upward
    assert discovered.path == path.resolve()
    validate_manifest(discovered.document, source=discovered.path)


def test_overwrite_needs_confirmation_and_leaves_the_file_alone(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    document = mw.compose_manifest(_inputs(), orchestrator_api="http://localhost:8000/api/v1")
    first = mw.write_manifest(root, document, force=True, confirm=lambda _q: False)
    assert first is mw.WriteOutcome.WRITTEN
    path = root / MANIFEST_FILENAME
    before = path.read_text(encoding="utf-8")

    different = dict(document, project_name="Renamed Project")
    with pytest.raises(InitError, match="--force"):
        mw.write_manifest(root, different, force=False, confirm=lambda _q: False)
    assert path.read_text(encoding="utf-8") == before

    confirmed = mw.write_manifest(root, different, force=False, confirm=lambda _q: True)
    assert confirmed is mw.WriteOutcome.WRITTEN
    assert json.loads(path.read_text(encoding="utf-8"))["project_name"] == "Renamed Project"


def test_force_rewrites_without_asking(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    document = mw.compose_manifest(_inputs(), orchestrator_api="http://localhost:8000/api/v1")
    mw.write_manifest(root, document, force=True, confirm=lambda _q: False)
    renamed = dict(document, project_name="Renamed")
    outcome = mw.write_manifest(
        root, renamed, force=True, confirm=lambda _q: pytest.fail("confirm must not run")
    )
    assert outcome is mw.WriteOutcome.WRITTEN


def test_unchanged_manifest_is_not_rewritten_or_prompted(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    document = mw.compose_manifest(_inputs(), orchestrator_api="http://localhost:8000/api/v1")
    mw.write_manifest(root, document, force=False, confirm=lambda _q: False)
    outcome = mw.write_manifest(
        root, document, force=False, confirm=lambda _q: pytest.fail("confirm must not run")
    )
    assert outcome is mw.WriteOutcome.UNCHANGED


def test_written_manifest_contains_no_secret_material(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    document = mw.compose_manifest(_inputs(), orchestrator_api="http://localhost:8000/api/v1")
    mw.write_manifest(root, document, force=True, confirm=lambda _q: False)
    text = (root / MANIFEST_FILENAME).read_text(encoding="utf-8")
    assert FIXTURE_TOKEN not in text
    assert "token" not in text.lower()
    assert "secret" not in text.lower()


# --- backend verification ------------------------------------------------------


def test_fetch_project_inputs_reads_backend_rows() -> None:
    fake = _fake()
    client = ApiClient(build_settings(), send=fake.send)
    inputs = mw.fetch_project_inputs(client, PID)
    assert inputs == mw.ProjectInputs(
        project_id=PID,
        name="Tea Factory ERP",
        default_branch="develop",
        branch_prefix="feat/{PID}-",
        audit_required_default=False,
    )
    assert [call.path for call in fake.calls] == [
        f"/api/v1/projects/{PID}",
        f"/api/v1/projects/{PID}/policy",
    ]


def test_fetch_maps_wrong_project_to_the_mismatch_family() -> None:
    fake = FakeBackend()
    fake.route(
        "GET",
        f"/api/v1/projects/{PID}",
        403,
        {
            "error": {
                "code": "AUTH_FORBIDDEN_PROJECT",
                "message": "token scoped elsewhere",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-test",
            }
        },
    )
    client = ApiClient(build_settings(), send=fake.send)
    with pytest.raises(InitError, match="AUTH_FORBIDDEN_PROJECT") as excinfo:
        mw.fetch_project_inputs(client, PID)
    assert "scoped to exactly one project" in str(excinfo.value)


def test_fetch_maps_unreachable_backend_to_a_clear_failure() -> None:
    def _refused(method: str, url: str, headers: Any, body: Any, timeout: float) -> WireResponse:
        raise ConnectionRefusedError("backend is down")

    client = ApiClient(build_settings(), send=_refused)
    with pytest.raises(InitError, match="backend unreachable"):
        mw.fetch_project_inputs(client, PID)


def test_fetch_rejects_a_malformed_project_id_before_any_call() -> None:
    fake = FakeBackend()
    client = ApiClient(build_settings(), send=fake.send)
    with pytest.raises(InitError, match="not a project id"):
        mw.fetch_project_inputs(client, "Tea Factory")
    assert fake.calls == []


def test_fetch_rejects_shape_drift_instead_of_guessing() -> None:
    fake = FakeBackend()
    fake.route("GET", f"/api/v1/projects/{PID}", 200, {"id": PID, "name": "Tea Factory ERP"})
    fake.route("GET", f"/api/v1/projects/{PID}/policy", 200, {"branch_prefix": "feat/{PID}-"})
    client = ApiClient(build_settings(), send=fake.send)
    with pytest.raises(InitError, match="default_branch"):
        mw.fetch_project_inputs(client, PID)


# --- the orchestrated flow (run_init) ------------------------------------------


def _args(*extra: str) -> Any:
    return build_parser().parse_args(["init", *extra])


def test_cli_flow_writes_stores_and_self_tests(
    tmp_path: Path, isolated_init_config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    subdir = _repo(tmp_path, "src", "nest")
    fake = _fake()
    code = run_init(
        _args("--project-id", PID),
        cwd=subdir,
        token_prompt=lambda _q: FIXTURE_TOKEN,
        send=_send_with_dynamic_end(fake),
    )
    assert code == EXIT_OK
    manifest = json.loads((tmp_path / "repo" / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["project_id"] == PID
    assert manifest["default_branch"] == "develop"
    assert manifest["audit_required_default"] is False
    assert load_settings(env={}, config_path=isolated_init_config).agent_token == FIXTURE_TOKEN
    captured = capsys.readouterr()
    assert "manifest written" in captured.out
    assert "self-test: all checks passed" in captured.out
    assert "mcpServers" in captured.out  # duty 4 only after the passing probe
    assert FIXTURE_TOKEN not in captured.out + captured.err


def test_cli_prompts_for_the_project_id_when_flag_is_absent(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    subdir = _repo(tmp_path)
    fake = _fake()
    asked: list[str] = []

    def _prompt(question: str) -> str:
        asked.append(question)
        return PID

    code = run_init(
        _args(),
        cwd=subdir,
        prompt=_prompt,
        token_prompt=lambda _q: FIXTURE_TOKEN,
        send=_send_with_dynamic_end(fake),
    )
    assert code == EXIT_OK
    assert len(asked) == 1 and "Project ID" in asked[0]


def test_cli_refuses_to_clobber_without_force(tmp_path: Path, isolated_init_config: Path) -> None:
    root = _repo(tmp_path)
    stale = {
        "schema_version": 1,
        "project_id": PID,
        "project_name": "Old Name",
        "orchestrator_api": "http://localhost:8000/api/v1",
        "default_branch": "main",
        "auto_branch_prefix": "feat/PID00007-",
        "audit_required_default": True,
    }
    (root / MANIFEST_FILENAME).write_text(json.dumps(stale), encoding="utf-8")
    fake = _fake()
    # pytest's stdin is not a TTY: the confirm declines → InitError naming --force.
    with pytest.raises(InitError, match="--force"):
        run_init(
            _args("--project-id", PID),
            cwd=root,
            token_prompt=lambda _q: FIXTURE_TOKEN,
            send=_send_with_dynamic_end(fake),
        )
    assert json.loads((root / MANIFEST_FILENAME).read_text(encoding="utf-8")) == stale

    code = run_init(
        _args("--project-id", PID, "--force"),
        cwd=root,
        token_prompt=lambda _q: FIXTURE_TOKEN,
        send=_send_with_dynamic_end(fake),
    )
    assert code == EXIT_OK
    replaced = json.loads((root / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert replaced["project_name"] == "Tea Factory ERP"


def test_cli_rejects_a_malformed_project_id_before_touching_the_backend(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo(tmp_path)
    fake = _fake()
    with pytest.raises(InitError, match="not a project id"):
        run_init(
            _args("--project-id", "tea-1"),
            cwd=root,
            token_prompt=lambda _q: FIXTURE_TOKEN,
            send=_send_with_dynamic_end(fake),
        )
    assert fake.calls == []
    assert not (root / MANIFEST_FILENAME).exists()


def test_cli_fails_loudly_when_the_backend_is_unreachable(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    root = _repo(tmp_path)

    def _refused(method: str, url: str, headers: Any, body: Any, timeout: float) -> WireResponse:
        raise ConnectionRefusedError("backend is down")

    with pytest.raises(InitError, match="backend unreachable"):
        run_init(
            _args("--project-id", PID),
            cwd=root,
            token_prompt=lambda _q: FIXTURE_TOKEN,
            send=_refused,
        )
    assert not (root / MANIFEST_FILENAME).exists()


def test_full_flow_keeps_the_token_out_of_the_working_tree(
    tmp_path: Path, isolated_init_config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """MT-2.12-02 AC: after init, no token-shaped content sits in the working tree.

    The first half of the AC (resolved config path not under the repo root) is
    pinned by ``test_init_token_storage.py``; this completes it with the
    post-init tree walk the AC asks for (FR-SEC-04; Section 20.4 item 3): the
    only copy of the token lives in the user-level config *outside* the repo.
    """
    leaf = _repo(tmp_path, "app", "src")
    fake = _fake()
    code = run_init(
        _args("--project-id", PID),
        cwd=leaf,
        token_prompt=lambda _q: FIXTURE_TOKEN,
        send=_send_with_dynamic_end(fake),
    )
    assert code == EXIT_OK
    root = tmp_path / "repo"
    scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        scanned += 1
        data = path.read_bytes()
        assert FIXTURE_TOKEN.encode() not in data, f"{path} carries the agent token"
        assert b"agent_token" not in data, f"{path} names the token key"
    assert scanned >= 1 and (root / MANIFEST_FILENAME).is_file()  # the walk saw real files
    capsys.readouterr()  # drain: the verdict/snippet lines are asserted elsewhere


def test_cli_withholds_snippets_when_the_probe_fails(
    tmp_path: Path, isolated_init_config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """MT-2.12-04 safe ordering: snippets print only after a passing self-test.

    Duties 1-2 still land (manifest + token) and the process exits non-zero
    with the per-check verdicts (MT-2.12-03's exit-code AC), but duty 4's
    registration blocks are withheld — no client config for an unproven
    binding.
    """
    root = _repo(tmp_path)
    fake = _fake()
    fake.route(
        "POST",
        "/api/v1/agent-sessions",
        401,
        {
            "error": {
                "code": "AUTH_REQUIRED",
                "message": "credential rejected on the probe",
                "retryable": False,
                "details": None,
                "correlation_id": "corr-test",
            }
        },
    )
    code = run_init(
        _args("--project-id", PID),
        cwd=root,
        token_prompt=lambda _q: FIXTURE_TOKEN,
        send=_send_with_dynamic_end(fake),
    )
    assert code == EXIT_FAILURE
    captured = capsys.readouterr()
    assert "self-test [session] FAIL" in captured.out
    assert "mcpServers" not in captured.out  # duty 4 gated on the passing probe
    assert FIXTURE_TOKEN not in captured.out + captured.err
    # Duties 1-2 completed before the gate: the write side is intact.
    assert (root / MANIFEST_FILENAME).is_file()
    assert load_settings(env={}, config_path=isolated_init_config).agent_token == FIXTURE_TOKEN


# --- the console entry (main) --------------------------------------------------


def test_main_renders_failures_as_one_scrubbed_stderr_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    code = main(["init", "--project-id", PID])
    assert code == EXIT_FAILURE
    captured = capsys.readouterr()
    assert captured.out == ""  # stdout stays clean for the flow's own output
    assert captured.err.count("\n") == 1
    assert "orchestrator init failed:" in captured.err
    assert "Traceback" not in captured.err
    assert FIXTURE_TOKEN not in captured.err


def test_main_standalone_self_test_fails_without_a_token(
    tmp_path: Path,
    isolated_init_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repo(tmp_path)
    monkeypatch.chdir(root)
    code = main(["init", "--self-test"])
    assert code == EXIT_FAILURE
    captured = capsys.readouterr()
    assert "self-test [token]" in captured.out and "FAIL" in captured.out
    assert "self-test: FAILED" in captured.out


def test_main_standalone_self_test_all_passes_against_loopback(
    tmp_path: Path,
    isolated_init_config: Path,
    stub_http_backend: StubHttpBackend,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _repo(tmp_path)
    document = {
        "schema_version": 1,
        "project_id": PID,
        "project_name": "Tea Factory ERP",
        "orchestrator_api": f"{stub_http_backend.origin}/api/v1",
        "default_branch": "main",
        "auto_branch_prefix": "feat/PID00007-",
        "audit_required_default": True,
    }
    (root / MANIFEST_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.chdir(root)
    monkeypatch.setenv("ORCHESTRATOR_AGENT_TOKEN", FIXTURE_TOKEN)
    code = main(["init", "--self-test"])
    assert code == EXIT_OK
    captured = capsys.readouterr()
    assert "self-test: all checks passed" in captured.out
    assert FIXTURE_TOKEN not in captured.out + captured.err
    # The probe session was opened and closed over the real socket.
    methods_paths = [(call.method, call.path) for call in stub_http_backend.requests]
    assert ("POST", "/api/v1/agent-sessions") in methods_paths
    assert any(path.endswith("/end") for _method, path in methods_paths)
