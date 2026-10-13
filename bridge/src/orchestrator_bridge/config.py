"""Configuration layering for the bridge: environment > user-level file > defaults.

(parent plan Sections 10.1 config responsibility, 10.3 step 3, 10.11; MT-2.1-02;
FR-SEC-04; NFR-10. Naming follows ``docs/plan/conventions/configuration.md``.)

Precedence — the documented reading of Section 10.3's "environment or user-level
config" (recorded in the WP changelog):

1. **environment variables** — exact-name lookup of the keys in ``_ENV_KEYS``
   only; foreign ``ORCHESTRATOR_*`` variables belong to other components and are
   ignored, and an exported-but-empty value counts as unset;
2. **user-level config file** — one TOML file at :func:`default_user_config_path`,
   anchored to the user profile, never inside a repository and never discovered
   from the current working directory (no ``.env`` autoloading — the manifest's
   upward walk of Section 10.3 is a different mechanism);
3. **built-in defaults** — the ``DEFAULT_*`` constants.

Sources deliberately NOT read: the manifest, any repo-tracked file, the cwd,
command-line arguments (MT-2.2-03 lists these as negative cases; FR-SEC-04).

Validation fails fast (NFR-10; Section 10.10): unknown file keys, malformed
values and mode-required keys raise :class:`ConfigError` with a message naming
the key and accepted values — never echoing a secret. The agent token is redacted
in ``repr()``; the logging layer scrubs it again at the single redaction point
(MT-2.1-03).
"""

from __future__ import annotations

import math
import os
import sys
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, cast

__all__ = [
    "ConfigError",
    "DEFAULT_API_BASE_URL",
    "DEFAULT_HTTP_HOST",
    "DEFAULT_HTTP_IDLE_TIMEOUT_SECONDS",
    "DEFAULT_HTTP_MAX_CONNECTIONS",
    "DEFAULT_HTTP_PORT",
    "DEFAULT_LOG_FORMAT",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_MAX_RESPONSE_MB",
    "DEFAULT_MODE",
    "DEFAULT_RETRY_BASE_DELAY_SECONDS",
    "DEFAULT_RETRY_MAX_ATTEMPTS",
    "DEFAULT_TIMEOUT_SECONDS",
    "LogFormat",
    "LogLevel",
    "REQUIRED_KEYS_BY_MODE",
    "RunMode",
    "Settings",
    "default_user_config_path",
    "load_settings",
    "validate_for_mode",
]

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "text"]


class RunMode(StrEnum):
    """The three run modes of parent plan Section 10.2."""

    STDIO = "stdio"
    HTTP = "http"
    MERGE_EXECUTOR = "merge-executor"


class ConfigError(Exception):
    """Fail-fast configuration problem: clear message, never a secret value."""


DEFAULT_API_BASE_URL: Final = "http://localhost:8000/api/v1"
DEFAULT_LOG_LEVEL: Final[LogLevel] = "INFO"
DEFAULT_LOG_FORMAT: Final[LogFormat] = "json"
DEFAULT_MODE: Final = RunMode.STDIO
DEFAULT_TIMEOUT_SECONDS: Final = 30.0
#: Response-size cap (MT-2.3-01; Section 9.10). 64 MB clears the Section 9.5
#: 25 MB attachment ceiling with base64 inflation (~33 MB) plus JSON overhead.
DEFAULT_MAX_RESPONSE_MB: Final = 64.0
#: Retry attempt bound (MT-2.3-02; Section 10.10): total attempts per call.
DEFAULT_RETRY_MAX_ATTEMPTS: Final = 3
#: First backoff delay (MT-2.3-02; Section 10.10): doubles each retry.
DEFAULT_RETRY_BASE_DELAY_SECONDS: Final = 1.0
#: HTTP/SSE run mode (WP-2.9; Section 10.2) — all four defaults are flagged
#: for review in the WP changelog: the plan fixes no numbers for them
#: (MT-2.9-03 risk note). Loopback-only bind by default (Section 12.4 accepts
#: local HTTP, and a wider bind is an explicit opt-in).
DEFAULT_HTTP_HOST: Final = "127.0.0.1"
#: Port 8765 avoids the backend's 8000 (DEFAULT_API_BASE_URL) — one default
#: never shadows the other stack component. ``0`` asks the OS for an ephemeral
#: port (tests; the bound address is logged at startup).
DEFAULT_HTTP_PORT: Final = 8765
#: Documented maximum concurrent connections (MT-2.9-03); conservative, so a
#: runaway client cannot grow the process unbounded.
DEFAULT_HTTP_MAX_CONNECTIONS: Final = 16
#: Documented idle-connection timeout in seconds (MT-2.9-03): no request and
#: no open SSE stream for this long and the connection is closed (best-effort
#: session end; the lease sweeper, Section 9.9, is the backend backstop).
DEFAULT_HTTP_IDLE_TIMEOUT_SECONDS: Final = 900.0

_LOG_LEVELS: Final[frozenset[str]] = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_LOG_FORMATS: Final[frozenset[str]] = frozenset({"json", "text"})

#: Section 10.4 step 2 vocabulary (WP-2.5 / MT-2.5-01; mirrors
#: ``capabilities.CAPABILITIES`` minus ``unknown`` — unset *is* unknown, so
#: an explicit unknown is rejected with guidance. Kept local so config.py
#: stays a stdlib-only leaf module.)
_SESSION_CAPABILITIES: Final[frozenset[str]] = frozenset({"vision", "text_only"})

# Settings attribute -> canonical environment variable (configuration.md: one
# canonical spelling, no aliases). The file key is the attribute name itself.
_ENV_KEYS: Final[Mapping[str, str]] = {
    "api_base_url": "ORCHESTRATOR_API_BASE_URL",
    "agent_token": "ORCHESTRATOR_AGENT_TOKEN",
    "manifest_path": "ORCHESTRATOR_BRIDGE_MANIFEST_PATH",
    "log_level": "ORCHESTRATOR_LOG_LEVEL",
    "log_format": "ORCHESTRATOR_LOG_FORMAT",
    "mode": "ORCHESTRATOR_BRIDGE_MODE",
    "timeout_seconds": "ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS",
    "max_response_mb": "ORCHESTRATOR_BRIDGE_MAX_RESPONSE_MB",
    "retry_max_attempts": "ORCHESTRATOR_BRIDGE_RETRY_MAX_ATTEMPTS",
    "retry_base_delay_seconds": "ORCHESTRATOR_BRIDGE_RETRY_BASE_DELAY_SECONDS",
    "merge_repo_paths": "ORCHESTRATOR_MERGE_REPO_PATHS",
    "http_host": "ORCHESTRATOR_BRIDGE_HTTP_HOST",
    "http_port": "ORCHESTRATOR_BRIDGE_HTTP_PORT",
    "http_max_connections": "ORCHESTRATOR_BRIDGE_HTTP_MAX_CONNECTIONS",
    "http_idle_timeout_seconds": "ORCHESTRATOR_BRIDGE_HTTP_IDLE_TIMEOUT_SECONDS",
    "session_capability": "ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY",
}
_FILE_KEYS: Final[frozenset[str]] = frozenset(_ENV_KEYS)


@dataclass(frozen=True, slots=True, repr=False)
class Settings:
    """The merged settings object every bridge module reads (one view, three layers)."""

    api_base_url: str
    agent_token: str | None
    manifest_path: Path | None
    log_level: LogLevel
    log_format: LogFormat
    mode: RunMode
    timeout_seconds: float
    max_response_mb: float
    retry_max_attempts: int
    retry_base_delay_seconds: float
    merge_repo_paths: tuple[str, ...]
    http_host: str
    http_port: int
    http_max_connections: int
    http_idle_timeout_seconds: float
    #: Section 10.4 step 2 / MT-2.5-01: the session's declared image
    #: capability (``vision``/``text_only``); unset = ``unknown`` (text-safe).
    session_capability: str | None

    def __repr__(self) -> str:
        """Debug-safe view — the token renders as [REDACTED] (FR-SEC-04)."""
        token = "[REDACTED]" if self.agent_token is not None else None
        return (
            f"Settings(api_base_url={self.api_base_url!r}, agent_token={token!r}, "
            f"manifest_path={self.manifest_path!r}, log_level={self.log_level!r}, "
            f"log_format={self.log_format!r}, mode={self.mode!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"max_response_mb={self.max_response_mb!r}, "
            f"retry_max_attempts={self.retry_max_attempts!r}, "
            f"retry_base_delay_seconds={self.retry_base_delay_seconds!r}, "
            f"merge_repo_paths={self.merge_repo_paths!r}, "
            f"http_host={self.http_host!r}, http_port={self.http_port!r}, "
            f"http_max_connections={self.http_max_connections!r}, "
            f"http_idle_timeout_seconds={self.http_idle_timeout_seconds!r}, "
            f"session_capability={self.session_capability!r})"
        )


def _config_base(platform: str, environ: Mapping[str, str]) -> Path:
    """Profile-anchored base directory for the user config (never the cwd)."""
    if platform == "win32":
        appdata = environ.get("APPDATA")
        return Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    xdg = environ.get("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else Path.home() / ".config"


def default_user_config_path() -> Path:
    """User-level config file: ``…/orchestrator/bridge.toml`` outside any repo.

    Windows: ``%APPDATA%\\orchestrator\\bridge.toml``; POSIX:
    ``${XDG_CONFIG_HOME:-~/.config}/orchestrator/bridge.toml``. TOML is the format
    fixed here for the read side; ``orchestrator init`` (WP-2.12 / MT-2.12-02)
    writes this path with the ``agent_token`` key.
    """
    return _config_base(sys.platform, os.environ) / "orchestrator" / "bridge.toml"


def _read_user_config(path: Path) -> Mapping[str, object]:
    """Read and schema-check the user file; a missing file means "no layer 2"."""
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"user config {path} is not valid TOML: {exc}") from None
    except UnicodeDecodeError:
        raise ConfigError(f"user config {path} is not valid UTF-8 text") from None
    except OSError as exc:
        raise ConfigError(f"cannot read user config {path}: {exc.strerror or exc}") from None
    unknown = sorted(set(data) - _FILE_KEYS)
    if unknown:
        allowed = ", ".join(sorted(_FILE_KEYS))
        raise ConfigError(
            f"unknown key(s) in user config {path}: {', '.join(unknown)}; allowed keys: {allowed}"
        )
    return data


def _pick(
    attr: str, file_values: Mapping[str, object], environ: Mapping[str, str]
) -> object | None:
    """Layer 1 (env) over layer 2 (file); ``None`` means "apply the default"."""
    env_raw = environ.get(_ENV_KEYS[attr])
    if env_raw is not None and env_raw.strip() != "":
        return env_raw
    if attr in file_values:
        return file_values[attr]
    return None


def _as_text(attr: str, value: object, *, secret: bool = False) -> str:
    if not isinstance(value, str):
        shown = "(secret value not shown)" if secret else repr(value)
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) must be a string, got {shown}") from None
    return value


def _positive_float(attr: str, value: object, *, unit: str) -> float:
    """Parse a finite number > 0 (timeout, size, delay); message names the key."""
    reason = f"must be a number of {unit} > 0, got {value!r}"
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) {reason}") from None
    try:
        parsed = float(value)
    except ValueError:
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) {reason}") from None
    if not math.isfinite(parsed) or parsed <= 0:
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) {reason}") from None
    return parsed


def _positive_int(attr: str, value: object) -> int:
    """Parse a whole number >= 1 (attempt count); message names the key."""
    reason = f"must be a positive whole number of attempts >= 1, got {value!r}"
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) {reason}") from None
    try:
        parsed = float(value)
    except ValueError:
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) {reason}") from None
    if not math.isfinite(parsed) or parsed < 1 or parsed != int(parsed):
        raise ConfigError(f"{_ENV_KEYS[attr]} ({attr}) {reason}") from None
    return int(parsed)


def load_settings(
    env: Mapping[str, str] | None = None,
    config_path: Path | None = None,
) -> Settings:
    """Resolve environment + user file + defaults into one validated settings object.

    ``env`` defaults to the process environment and ``config_path`` to
    :func:`default_user_config_path`; tests inject both. Raises
    :class:`ConfigError` on any unknown key or malformed value (fail fast at
    startup, NFR-10). Never prints or returns anything that reveals a secret.
    """
    environ = os.environ if env is None else env
    path = default_user_config_path() if config_path is None else config_path
    file_values = _read_user_config(path)

    value = _pick("api_base_url", file_values, environ)
    api_base_url = DEFAULT_API_BASE_URL if value is None else _as_text("api_base_url", value)
    if not api_base_url.startswith(("http://", "https://")):
        raise ConfigError(
            f"{_ENV_KEYS['api_base_url']} (api_base_url) must be an http(s):// URL, "
            f"got {api_base_url!r}"
        ) from None

    value = _pick("agent_token", file_values, environ)
    agent_token: str | None = None
    if value is not None:
        raw_token = _as_text("agent_token", value, secret=True).strip()
        agent_token = raw_token or None

    value = _pick("manifest_path", file_values, environ)
    manifest_path: Path | None = None
    if value is not None:
        raw_manifest = _as_text("manifest_path", value).strip()
        manifest_path = Path(raw_manifest) if raw_manifest else None

    value = _pick("log_level", file_values, environ)
    raw_level = DEFAULT_LOG_LEVEL if value is None else _as_text("log_level", value)
    level = raw_level.strip().upper()
    if level not in _LOG_LEVELS:
        raise ConfigError(
            f"{_ENV_KEYS['log_level']} (log_level) must be one of "
            f"{', '.join(sorted(_LOG_LEVELS))}; got {raw_level!r}"
        ) from None
    log_level = cast(LogLevel, level)  # membership checked above

    value = _pick("log_format", file_values, environ)
    raw_format = DEFAULT_LOG_FORMAT if value is None else _as_text("log_format", value)
    fmt = raw_format.strip().lower()
    if fmt not in _LOG_FORMATS:
        raise ConfigError(
            f"{_ENV_KEYS['log_format']} (log_format) must be one of "
            f"{', '.join(sorted(_LOG_FORMATS))}; got {raw_format!r}"
        ) from None
    log_format = cast(LogFormat, fmt)  # membership checked above

    value = _pick("mode", file_values, environ)
    raw_mode = DEFAULT_MODE.value if value is None else _as_text("mode", value)
    try:
        mode = RunMode(raw_mode.strip().lower())
    except ValueError:
        choices = ", ".join(run_mode.value for run_mode in RunMode)
        raise ConfigError(
            f"{_ENV_KEYS['mode']} (mode) must be one of {choices}; got {raw_mode!r}"
        ) from None

    value = _pick("timeout_seconds", file_values, environ)
    timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    if value is not None:
        timeout_seconds = _positive_float("timeout_seconds", value, unit="seconds")

    value = _pick("max_response_mb", file_values, environ)
    max_response_mb = DEFAULT_MAX_RESPONSE_MB
    if value is not None:
        max_response_mb = _positive_float("max_response_mb", value, unit="MB")

    value = _pick("retry_max_attempts", file_values, environ)
    retry_max_attempts = DEFAULT_RETRY_MAX_ATTEMPTS
    if value is not None:
        retry_max_attempts = _positive_int("retry_max_attempts", value)

    value = _pick("retry_base_delay_seconds", file_values, environ)
    retry_base_delay_seconds = DEFAULT_RETRY_BASE_DELAY_SECONDS
    if value is not None:
        retry_base_delay_seconds = _positive_float(
            "retry_base_delay_seconds", value, unit="seconds"
        )

    value = _pick("merge_repo_paths", file_values, environ)
    merge_repo_paths: tuple[str, ...] = ()
    if isinstance(value, str):
        merge_repo_paths = tuple(item.strip() for item in value.split(",") if item.strip())
    elif isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        merge_repo_paths = tuple(item.strip() for item in value if isinstance(item, str))
    elif value is not None:
        raise ConfigError(
            f"{_ENV_KEYS['merge_repo_paths']} (merge_repo_paths) must be a list of paths "
            f"(env: comma-separated); got {value!r}"
        ) from None

    # --- HTTP/SSE run mode listen + connection bounds (WP-2.9; Section 10.2) --
    value = _pick("http_host", file_values, environ)
    http_host = DEFAULT_HTTP_HOST if value is None else _as_text("http_host", value).strip()
    if not http_host or any(ch.isspace() for ch in http_host) or "://" in http_host:
        raise ConfigError(
            f"{_ENV_KEYS['http_host']} (http_host) must be a bare host or IP "
            f"(default {DEFAULT_HTTP_HOST}); got {http_host!r}"
        ) from None

    value = _pick("http_port", file_values, environ)
    http_port = DEFAULT_HTTP_PORT
    if value is not None:
        raw_port = _as_text("http_port", value).strip()
        try:
            http_port = int(raw_port)
        except ValueError:
            raise ConfigError(
                f"{_ENV_KEYS['http_port']} (http_port) must be a whole number "
                f"0-65535 (0 = ephemeral); got {raw_port!r}"
            ) from None
        if not 0 <= http_port <= 65535:
            raise ConfigError(
                f"{_ENV_KEYS['http_port']} (http_port) must be 0-65535 "
                f"(0 = ephemeral); got {http_port}"
            ) from None

    value = _pick("http_max_connections", file_values, environ)
    http_max_connections = DEFAULT_HTTP_MAX_CONNECTIONS
    if value is not None:
        http_max_connections = _positive_int("http_max_connections", value)

    value = _pick("http_idle_timeout_seconds", file_values, environ)
    http_idle_timeout_seconds = DEFAULT_HTTP_IDLE_TIMEOUT_SECONDS
    if value is not None:
        http_idle_timeout_seconds = _positive_float(
            "http_idle_timeout_seconds", value, unit="seconds"
        )

    # --- Section 10.4 step 2: the session's declared image capability ------
    # (WP-2.5 / MT-2.5-01). Unset = unknown = text-safe; only the two
    # declared capabilities are accepted — the bridge never infers vision
    # (ADR-006). Kept out of REQUIRED_KEYS_BY_MODE: every mode runs fine
    # with the honest text-safe default.
    value = _pick("session_capability", file_values, environ)
    session_capability: str | None = None
    if value is not None:
        raw_capability = _as_text("session_capability", value).strip().lower()
        if raw_capability and raw_capability not in _SESSION_CAPABILITIES:
            raise ConfigError(
                f"{_ENV_KEYS['session_capability']} (session_capability) must be one of "
                f"{', '.join(sorted(_SESSION_CAPABILITIES))} (or unset for the text-safe "
                f"default); got {value!r}"
            ) from None
        session_capability = raw_capability or None

    return Settings(
        api_base_url=api_base_url,
        agent_token=agent_token,
        manifest_path=manifest_path,
        log_level=log_level,
        log_format=log_format,
        mode=mode,
        timeout_seconds=timeout_seconds,
        max_response_mb=max_response_mb,
        retry_max_attempts=retry_max_attempts,
        retry_base_delay_seconds=retry_base_delay_seconds,
        merge_repo_paths=merge_repo_paths,
        http_host=http_host,
        http_port=http_port,
        http_max_connections=http_max_connections,
        http_idle_timeout_seconds=http_idle_timeout_seconds,
        session_capability=session_capability,
    )


# Mode-required keys (MT-2.1-02 scope): parent plan Section 10.2 fixes each mode's
# binding source — STDIO binds by working directory, HTTP per connection, and the
# Merge Executor by "config listing allowed repo paths", so only the executor has
# a startup requirement today.
REQUIRED_KEYS_BY_MODE: Final[Mapping[RunMode, frozenset[str]]] = {
    RunMode.STDIO: frozenset(),
    RunMode.HTTP: frozenset(),
    RunMode.MERGE_EXECUTOR: frozenset({"merge_repo_paths"}),
}

_UNSET_CHECKS: Final[Mapping[str, Callable[[Settings], bool]]] = {
    "agent_token": lambda settings: settings.agent_token is None,
    "manifest_path": lambda settings: settings.manifest_path is None,
    "merge_repo_paths": lambda settings: not settings.merge_repo_paths,
}


def validate_for_mode(settings: Settings, mode: RunMode) -> None:
    """Fail fast when a key required by the selected run mode is missing (NFR-10).

    The message names both legitimate sources (env var and user-config key) and
    never echoes a value.
    """
    required = REQUIRED_KEYS_BY_MODE[mode]
    missing = sorted(key for key in required if _UNSET_CHECKS[key](settings))
    if missing:
        hints = ", ".join(
            f"{_ENV_KEYS[key]} (env) or '{key}' (user config file)" for key in missing
        )
        raise ConfigError(
            f"missing configuration required for mode '{mode.value}': {hints}"
        ) from None
