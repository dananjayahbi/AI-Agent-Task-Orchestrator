"""MT-2.2-03 — agent token loading: sourcing precedence, shape gate, no leak.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.2-manifest-binding/
MT-2.2-03-token-loading.md (parent plan Sections 10.3 step 3, 10.11, 12.2,
19.1; FR-SEC-01, FR-SEC-04, FR-MCP-06).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from orchestrator_bridge.config import _ENV_KEYS, Settings, load_settings
from orchestrator_bridge.credentials import require_agent_token
from orchestrator_bridge.errors import INIT_COMMAND, ManifestValidationError, TokenError
from orchestrator_bridge.manifest import StartupBinding, bind_startup

ABSENT_CONFIG = Path("no-such-bridge-config.toml")
ENV_KEY = _ENV_KEYS["agent_token"]  # ORCHESTRATOR_AGENT_TOKEN — one canonical name


def _settings(env: dict[str, str] | None = None, config_path: Path = ABSENT_CONFIG) -> Settings:
    return load_settings(env=env or {}, config_path=config_path)


# --- sourcing: environment over user-level config, never the manifest ---------


def test_env_token_wins_over_user_file(tmp_path: Path) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text('agent_token = "file-level-token"\n', encoding="utf-8")
    settings = _settings({ENV_KEY: "env-level-token"}, config_path=config)

    assert require_agent_token(settings) == "env-level-token"


def test_user_file_token_is_accepted_when_env_absent(tmp_path: Path) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text('agent_token = "file-level-token"\n', encoding="utf-8")
    settings = _settings(config_path=config)

    assert require_agent_token(settings) == "file-level-token"


def test_env_token_round_trips_unchanged() -> None:
    """Shape-check only: the value is handed back verbatim for the backend to
    verify (FR-SEC-01) — the bridge never rewrites it (Section 12.2)."""
    settings = _settings({ENV_KEY: "pat-style.opaque-token_12345"})
    assert require_agent_token(settings) == "pat-style.opaque-token_12345"


def test_manifest_planted_token_is_never_read(
    tmp_path: Path,
    minimal_manifest: dict[str, object],
    write_manifest: Callable[..., Path],
) -> None:
    """FR-SEC-04 belt-and-braces: a token smuggled into a fixture manifest is
    rejected structurally (allowlist) *and* invisible to the loader — the gate
    still fails on the missing env/user token, never on the planted value."""
    manifest = write_manifest(
        tmp_path / "repo", document={**minimal_manifest, "agent_token": "planted-token-value"}
    )
    settings = _settings()  # no env token, no user config

    # The loader never consults the manifest: the token stays unset.
    assert settings.agent_token is None
    # And the binding flow rejects the document before any credential step.
    with pytest.raises(ManifestValidationError) as excinfo:
        bind_startup(settings, cwd=manifest.parent)
    assert "planted-token-value" not in str(excinfo.value)


# --- missing token: fail fast, name both sources, leak nothing ----------------


def test_missing_token_names_env_var_and_init_command() -> None:
    settings = _settings()
    assert settings.agent_token is None

    with pytest.raises(TokenError) as excinfo:
        require_agent_token(settings)
    message = str(excinfo.value)
    assert ENV_KEY in message  # source 1: environment variable
    assert INIT_COMMAND in message  # source 2: init stores it user-level
    assert "not configured" in message


def test_missing_token_message_contains_no_secret_material() -> None:
    with pytest.raises(TokenError) as excinfo:
        require_agent_token(_settings())
    message = str(excinfo.value)
    assert "=" not in message  # nothing value-shaped (token=..., key: ...)
    assert "None" not in message  # the unset state is never echoed as data
    assert "Bearer" not in message


def test_whitespace_only_token_counts_as_missing() -> None:
    """The loader collapses empty/whitespace values to None (MT-2.1-02), so the
    gate reports "not configured" rather than a broken header later."""
    settings = _settings({ENV_KEY: "   "})
    assert settings.agent_token is None
    with pytest.raises(TokenError, match="not configured"):
        require_agent_token(settings)


# --- header safety: shape check only, no local verification -------------------


def test_inner_whitespace_token_rejected_as_unsafe_header() -> None:
    """Whitespace inside the value would split/inject the Authorization line
    (Section 12.2) — rejected at load time, message does not echo the value."""
    settings = _settings({ENV_KEY: "abc def"})
    with pytest.raises(TokenError) as excinfo:
        require_agent_token(settings)
    message = str(excinfo.value)
    assert "valid bearer value" in message
    assert "abc def" not in message
    assert ENV_KEY in message or "user config" in message


def test_control_character_token_rejected_as_unsafe_header() -> None:
    settings = _settings({ENV_KEY: "abc\x00def"})
    with pytest.raises(TokenError) as excinfo:
        require_agent_token(settings)
    assert "valid bearer value" in str(excinfo.value)
    assert "abc\x00def" not in str(excinfo.value)


def test_loader_contains_no_crypto_or_decode_logic() -> None:
    """FR-SEC-01 split: no signature/expiry/revocation checking locally — an
    opaque bearer value is verified by the backend when the session opens."""
    source = Path(require_agent_token.__code__.co_filename).read_text(encoding="utf-8")
    forbidden = (
        "import base64",
        "import hmac",
        "import hashlib",
        "import jwt",
        "cryptography",
        ".decode(",
        "urlsafe",
    )
    leaked = [name for name in forbidden if name in source]
    assert leaked == [], f"local verification primitives leaked: {leaked}"


# --- Section 10.3 ordering: 1 discover, 2 validate, 3 token -------------------


def test_invalid_manifest_aborts_before_token_gate(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    """FR-SEC-01 hygiene: an invalid manifest never gets near a credential —
    even with no token configured, the manifest error is what surfaces."""
    manifest = write_manifest(tmp_path / "repo")
    manifest.write_text('{"schema_version": 1, "project_id": "nope"}', encoding="utf-8")
    settings = _settings()  # token absent as well

    with pytest.raises(ManifestValidationError):
        bind_startup(settings, cwd=manifest.parent)


def test_valid_manifest_without_token_stops_at_token_gate(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    manifest = write_manifest(tmp_path / "repo")
    settings = _settings()

    with pytest.raises(TokenError):
        bind_startup(settings, cwd=manifest.parent)


def test_full_binding_succeeds_with_manifest_and_token(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    manifest = write_manifest(tmp_path / "repo")
    settings = _settings({ENV_KEY: "fixture-token-not-a-real-secret"})

    binding = bind_startup(settings, cwd=manifest.parent)
    assert isinstance(binding, StartupBinding)
    assert binding.project_id == "PID00007"
    assert binding.manifest_path == manifest.resolve()
    # The token stays in Settings — deliberately absent from the binding result.
    assert not hasattr(binding, "agent_token")
