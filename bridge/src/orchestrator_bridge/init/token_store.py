"""Agent-token acquisition and user-level storage (FR-MCP-08 duty 2; FR-SEC-04; MT-2.12-02).

The write side of MT-2.1-02's config contract and MT-2.2-03's read contract:
this module produces exactly the file the loader accepts — one flat TOML at
:func:`orchestrator_bridge.config.default_user_config_path` under the
``agent_token`` key (``ORCHESTRATOR_AGENT_TOKEN``'s file-layer counterpart).

Rules fixed here (parent plan Sections 10.11, 12.2; FR-SEC-04):

* **Input** — environment first (headless/CI init), else a *hidden* prompt.
  The token never rides in argv (process lists, shell history) and is never
  echoed back, logged or embedded in an error message; empty or header-unsafe
  values are refused without showing what was typed.
* **Destination** — the user profile's config dir, never the working tree;
  :func:`store_agent_token` refuses a path inside the repository outright
  (a cwd-relative "user config" would violate FR-SEC-04 by construction).
* **Merge** — re-init replaces only the ``agent_token`` line; every other key
  (and comment) already in the file survives. The pre-existing file is
  validated with the loader's own check first, and the merged text is parsed
  back before writing, so init can neither persist nor leave behind a file
  the loader would reject.
* **Permissions** — owner-only where the platform supports it: ``0600`` on
  the file and ``0700`` on the config directory on POSIX. Windows has no
  POSIX permission bits; the file relies on the user-profile location's ACLs
  (``%APPDATA%`` is per-user) — recorded in the WP changelog rather than
  claiming POSIX guarantees everywhere.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

from ..config import _ENV_KEYS, ConfigError, _read_user_config, default_user_config_path
from ..credentials import _header_safe
from ..errors import INIT_COMMAND, InitError

__all__ = ["acquire_token", "store_agent_token"]

#: The hidden-prompt label — says "hidden" so a paste is expected, not read.
_TOKEN_PROMPT: Final = "Agent token (input hidden, never argv): "

_KEY_LINE: Final = re.compile(r"^\s*agent_token\s*=")


def _require_header_safe(token: str) -> None:
    """Refuse an unheaderable value without echoing any of it (Section 12.2)."""
    if not _header_safe(token):
        raise InitError(
            f"the agent token from {_ENV_KEYS['agent_token']} or the prompt "
            "contains whitespace or control characters, so it cannot be a "
            "bearer header value; fix the value (it is never echoed) and "
            f"re-run '{INIT_COMMAND}'"
        )


def acquire_token(
    *,
    environ: Mapping[str, str] | None = None,
    prompt: Callable[[str], str] | None = None,
    stdin_isatty: bool | None = None,
) -> str:
    """Return the token the user provides — environment, else hidden prompt.

    ``prompt`` and ``stdin_isatty`` are test seams; production uses the
    process environment and :func:`getpass.getpass`, refusing a headless run
    with no environment value (no silent empty token). The value is validated
    for header safety on *both* paths so a broken token fails here, not at
    the first backend call.
    """
    env = os.environ if environ is None else environ
    from_env = env.get(_ENV_KEYS["agent_token"], "")
    if from_env.strip():
        token = from_env.strip()
        _require_header_safe(token)
        return token

    if prompt is None:
        interactive = sys.stdin.isatty() if stdin_isatty is None else stdin_isatty
        if not interactive:
            raise InitError(
                f"agent token not configured and no terminal is available for "
                f"a hidden prompt: set {_ENV_KEYS['agent_token']} for headless "
                f"init, then re-run '{INIT_COMMAND}'"
            )
        prompt = getpass.getpass
    try:
        typed = prompt(_TOKEN_PROMPT)
    except (EOFError, KeyboardInterrupt):
        raise InitError(
            "agent token prompt cancelled; re-run and paste the token, or set "
            f"{_ENV_KEYS['agent_token']} for headless init"
        ) from None
    token = typed.strip()
    if not token:
        raise InitError(
            f"no agent token given; paste the token issued for this project, "
            f"or set {_ENV_KEYS['agent_token']}, then re-run '{INIT_COMMAND}'"
        )
    _require_header_safe(token)
    return token


def _toml_basic_string(value: str) -> str:
    """Encode *value* as a TOML basic string (JSON's escaping is a subset).

    Only header-safe values reach this function (no control characters), so
    the JSON string form — quotes and backslash escaped — is valid TOML; the
    raw form is written as UTF-8 so non-ASCII survives without surrogate
    escapes, which TOML rejects.
    """
    return json.dumps(value, ensure_ascii=False)


def _set_key_line(text: str, key: str, value: str) -> str:
    """Replace (or append) the one top-level ``key = ...`` line in *text*.

    Line-based so unrelated keys *and comments* survive a re-init; duplicate
    ``key`` lines collapse to one (the new value), which the caller's parse-
    back check then confirms is loadable.
    """
    line = f"{key} = {_toml_basic_string(value)}"
    if not text.strip():
        return line + "\n"
    output: list[str] = []
    replaced = False
    for existing in text.splitlines():
        if _KEY_LINE.match(existing):
            if not replaced:
                output.append(line)
                replaced = True
            continue  # drop any duplicate key line
        output.append(existing)
    if not replaced:
        output.append(line)
    return "\n".join(output) + "\n"


def store_agent_token(
    token: str,
    *,
    config_path: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    """Merge *token* into the user-level config under ``agent_token``.

    Returns the file's path (the only thing callers may print — never the
    value). ``repo_root`` arms the FR-SEC-04 guard: a config path resolving
    inside the repository is refused outright. Permissions are tightened on
    POSIX after a successful write; a failure mid-write leaves the previous
    file intact (the merged text is fully built and re-parsed first).
    """
    stripped = token.strip()
    if not stripped:
        raise InitError(
            f"refusing to store an empty agent token; re-run '{INIT_COMMAND}' "
            f"and provide the token issued for this project"
        )
    _require_header_safe(stripped)

    path = config_path if config_path is not None else default_user_config_path()
    resolved = path.expanduser()
    if repo_root is not None and resolved.is_relative_to(repo_root.resolve()):
        raise InitError(
            f"refusing to store the agent token inside the repository "
            f"({resolved}): repo-tracked files must never carry secrets "
            "(FR-SEC-04); the user-level config lives outside the working "
            "tree — unset any config-path override and re-run"
        )

    existing_text = ""
    if resolved.is_file():
        try:
            _read_user_config(resolved)  # the loader's own key check
            existing_text = resolved.read_text(encoding="utf-8")
        except ConfigError as exc:
            raise InitError(f"existing user config {resolved} cannot be updated: {exc}") from None
        except (OSError, UnicodeDecodeError) as exc:
            raise InitError(f"cannot read the user config {resolved}: {exc}") from None

    merged = _set_key_line(existing_text, "agent_token", stripped)
    try:
        parsed = tomllib.loads(merged)
    except tomllib.TOMLDecodeError as exc:
        raise InitError(
            f"merging the agent token into {resolved} would produce invalid "
            f"TOML ({exc}); fix the existing file and re-run '{INIT_COMMAND}'"
        ) from None
    if parsed.get("agent_token") != stripped:  # pragma: no cover - parse-back guard
        raise InitError(f"token merge into {resolved} did not round-trip; aborting")

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(merged, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise InitError(f"cannot write the user config {resolved}: {exc.strerror or exc}") from None
    if os.name == "posix":  # Windows: user-profile ACLs instead (module docstring)
        os.chmod(resolved.parent, 0o700)
        os.chmod(resolved, 0o600)
    return resolved
