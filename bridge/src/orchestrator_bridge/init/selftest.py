"""Connectivity self-test of ``orchestrator init`` (FR-MCP-08 duty 3; NFR-10; MT-2.12-03).

Three checks, in FR-MCP-08 order, each a one-line verdict with remedy text:

1. **Manifest** — discovery + the shared schema validator (MT-2.2-01/02),
   local and instant.
2. **Token** — MT-2.2-03's loader plus its own ``require_agent_token`` gate;
   the verdict names the *source* that supplied the value (environment or
   user-level config path), never the value itself.
3. **Session probe** — the real Section 10.3 steps 4–5 through MT-2.2-04's
   :func:`open_session` (single implementation, Section 19.6): one call
   verifies credential, project binding and reachability together (an
   unauthenticated ping would pass on a wrong-project token), then
   :func:`close_session` ends the probe session so init leaks none. A
   wrong-project token lands on MT-2.2-05's
   :class:`ProjectMismatchError` message verbatim.

The probe is bounded by the transport's retry policy (Section 10.10: fixed
attempt budget with backoff — no indefinite hangs) and the verdicts are
read-only: no manifest or config mutation, no secret in output or logs. Exit
semantics live with the caller: every check must read ``pass`` or the run
fails (a ``skip`` means a prerequisite already failed).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from ..config import _ENV_KEYS, ConfigError, Settings, default_user_config_path, load_settings
from ..credentials import require_agent_token
from ..errors import (
    INIT_COMMAND,
    BindingError,
    ProjectMismatchError,
    SessionOpenError,
    TokenError,
)
from ..logging import get_logger
from ..manifest import StartupBinding
from ..manifest_discovery import discover_manifest
from ..manifest_validation import validate_manifest
from ..session import close_session, open_session
from ..transport import ApiClient, SendFn

CheckStatus = Literal["pass", "fail", "skip"]

__all__ = ["CheckResult", "all_passed", "run_self_test"]

_LOGGER_COMPONENT: Final = "init"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One self-test verdict: name, status, safe detail, optional remedy."""

    name: str
    status: CheckStatus
    detail: str
    remedy: str | None = None

    @property
    def ok(self) -> bool:
        """Only ``pass`` counts — a skip means a prerequisite failed."""
        return self.status == "pass"


def all_passed(results: tuple[CheckResult, ...] | list[CheckResult]) -> bool:
    """Whether every check passed (the exit-zero condition)."""
    return bool(results) and all(result.ok for result in results)


def _manifest_check(
    start: Path, override: Path | None
) -> tuple[CheckResult, StartupBinding | None]:
    try:
        discovered = discover_manifest(start, override=override)
        validated = validate_manifest(discovered.document, source=discovered.path)
    except BindingError as exc:
        return (
            CheckResult(
                "manifest",
                "fail",
                str(exc),
                remedy=f"fix the manifest, or run '{INIT_COMMAND}' to (re)write it",
            ),
            None,
        )
    binding = StartupBinding(manifest_path=discovered.path, manifest=validated)
    return (
        CheckResult(
            "manifest",
            "pass",
            f"{discovered.path} (project {binding.project_id}, schema v1)",
        ),
        binding,
    )


def _token_check(
    environ: Mapping[str, str], config_path: Path
) -> tuple[CheckResult, Settings | None]:
    try:
        settings = load_settings(env=environ, config_path=config_path)
    except ConfigError as exc:
        return (
            CheckResult(
                "token",
                "fail",
                f"configuration unreadable: {exc}",
                remedy="fix the user config file or the ORCHESTRATOR_* values it sets",
            ),
            None,
        )
    try:
        require_agent_token(settings)
    except TokenError as exc:
        return (
            CheckResult(
                "token",
                "fail",
                str(exc),
                remedy=(
                    f"export {_ENV_KEYS['agent_token']} or run "
                    f"'{INIT_COMMAND}' to store one in {config_path}"
                ),
            ),
            None,
        )
    from_env = environ.get(_ENV_KEYS["agent_token"], "").strip()
    source = "environment" if from_env else f"user-level config ({config_path})"
    return CheckResult("token", "pass", f"source: {source}"), settings


def _session_check(
    binding: StartupBinding,
    settings: Settings,
    config_path: Path,
    send: SendFn | None,
    sleep: Callable[[float], None] | None,
) -> CheckResult:
    try:
        client = ApiClient.for_binding(
            binding,
            settings,
            send=send,
            sleep=sleep if sleep is not None else time.sleep,
        )
        session = open_session(binding, settings, client=client)
    except ProjectMismatchError as exc:
        # MT-2.2-05's message already carries the fix; keep it as the detail.
        return CheckResult(
            "session",
            "fail",
            str(exc),
            remedy=(
                "use the token issued for this project, or run "
                f"'{INIT_COMMAND}' in the repository that matches the token"
            ),
        )
    except SessionOpenError as exc:
        return CheckResult(
            "session",
            "fail",
            str(exc),
            remedy=(
                "check the endpoint (manifest orchestrator_api / "
                "ORCHESTRATOR_API_BASE_URL) and the token, then re-run the "
                "self-test"
            ),
        )
    ended = close_session(binding, settings, session, send=send)
    detail = (
        f"opened and closed a probe session for {binding.project_id}"
        if ended
        else (
            f"opened a probe session for {binding.project_id}; the end call "
            "was not confirmed (backend staleness handling covers it)"
        )
    )
    return CheckResult("session", "pass", detail)


def run_self_test(
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    config_path: Path | None = None,
    send: SendFn | None = None,
    sleep: Callable[[float], None] | None = None,
) -> tuple[CheckResult, ...]:
    """Run the three checks and return their verdicts (read-only, no raise).

    *cwd* defaults to the process working directory; *env* to the process
    environment; *config_path* to the user-level config the loader uses.
    ``send`` is the transport seam (init hands its own client's seam through
    so one backend fake serves the whole flow); ``sleep`` bounds retry waits
    in tests. Each check logs one structured record (MT-2.1-03) and never
    includes the token value.
    """
    start = Path.cwd() if cwd is None else cwd
    environ = os.environ if env is None else env
    cfg = default_user_config_path() if config_path is None else config_path

    override_raw = environ.get(_ENV_KEYS["manifest_path"], "").strip()
    override = Path(override_raw) if override_raw else None

    manifest_result, binding = _manifest_check(start, override)
    token_result, settings = _token_check(environ, cfg)

    if binding is not None and settings is not None:
        session_result = _session_check(binding, settings, cfg, send, sleep)
    else:
        failed = manifest_result if binding is None else token_result
        session_result = CheckResult(
            "session",
            "skip",
            f"skipped: the {failed.name} check failed first",
            remedy=failed.remedy,
        )

    results = (manifest_result, token_result, session_result)
    logger = get_logger(_LOGGER_COMPONENT)
    for result in results:
        logger.info(
            "self-test check",
            extra={
                "event": "selftest_check",
                "check": result.name,
                "status": result.status,
            },
        )
    return results
