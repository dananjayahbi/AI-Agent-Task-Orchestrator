"""Boot and settings smoke tests (MT-1.1-01; parent plan Sections 9.10, 16.2, 20.4).

Each test runs ``manage.py check`` in a subprocess with a scrubbed environment,
so the assertion is a real boot — settings import plus project validation — for
the target environment, not an in-process shortcut. The prod cases prove the
Section 16.2 fail-fast behaviour: weak, missing and debug-on configurations
refuse to boot, naming the offending variable (never its value), while a fully
specified strong configuration passes.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Placeholder-free, >= 32 chars — meets the documented prod strength rules.
_STRONG_SECRET_KEY = "smoke-run-key-a1b2c3d4e5f6g7h8i9j0klmnopqrstuvw"  # pragma: allowlist secret
_STRONG_DATABASE_PASSWORD = "smoke-db-pass-1a2b3c4d5e6f"  # pragma: allowlist secret


def _clean_env() -> dict[str, str]:
    """Inherit the process environment minus every settings-module input."""
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("ORCHESTRATOR_") and key != "DJANGO_SETTINGS_MODULE"
    }


def _run_manage_check(overrides: dict[str, str]) -> tuple[int, str]:
    """Run ``manage.py check`` with *overrides* applied to a scrubbed environment."""
    env = {**_clean_env(), **overrides}
    result = subprocess.run(  # noqa: S603
        [sys.executable, "manage.py", "check"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        check=False,
        timeout=120,
    )
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    return result.returncode, output


def _prod_base_env() -> dict[str, str]:
    """A complete, strong production configuration (all required-in-prod names).

    Selects the prod module explicitly — the same mechanism the container image
    uses (backend/Dockerfile sets DJANGO_SETTINGS_MODULE); on a host, manage.py
    would default to dev and bypass the prod rules by design.
    """
    return {
        "DJANGO_SETTINGS_MODULE": "apps.core.settings.prod",
        "ORCHESTRATOR_DEBUG": "false",
        "ORCHESTRATOR_SECRET_KEY": _STRONG_SECRET_KEY,
        "ORCHESTRATOR_ALLOWED_HOSTS": "orchestrator.example.internal",
        "ORCHESTRATOR_DATABASE_PASSWORD": _STRONG_DATABASE_PASSWORD,
    }


def test_dev_environment_boots_without_any_environment() -> None:
    """Dev settings boot on a fresh clone: no env, no committed secrets (20.4 item 3)."""
    returncode, output = _run_manage_check({})
    assert returncode == 0, f"dev boot failed:\n{output}"
    assert "System check identified no issues" in output


def test_prod_boots_with_strong_values() -> None:
    """A fully specified, non-weak prod configuration passes startup validation."""
    returncode, output = _run_manage_check(_prod_base_env())
    assert returncode == 0, f"prod boot with strong values failed:\n{output}"


def test_prod_refuses_missing_secret_key() -> None:
    """Missing ORCHESTRATOR_SECRET_KEY fails fast, naming the variable (16.2)."""
    env = _prod_base_env()
    del env["ORCHESTRATOR_SECRET_KEY"]
    returncode, output = _run_manage_check(env)
    assert returncode != 0, "prod boot must fail without ORCHESTRATOR_SECRET_KEY"
    assert "ORCHESTRATOR_SECRET_KEY" in output


def test_prod_refuses_weak_secret_key() -> None:
    """A placeholder/weak ORCHESTRATOR_SECRET_KEY fails fast (16.2, 20.4 item 3)."""
    env = _prod_base_env()
    env["ORCHESTRATOR_SECRET_KEY"] = "change-me"  # pragma: allowlist secret
    returncode, output = _run_manage_check(env)
    assert returncode != 0, "prod boot must refuse the placeholder secret"
    assert "ORCHESTRATOR_SECRET_KEY" in output
    # The error names the variable but never echoes its value.
    assert "change-me" not in output


def test_prod_refuses_debug_mode() -> None:
    """ORCHESTRATOR_DEBUG=true is refused in prod (configuration.md, Section 16.2)."""
    env = _prod_base_env()
    env["ORCHESTRATOR_DEBUG"] = "true"
    returncode, output = _run_manage_check(env)
    assert returncode != 0, "prod boot must refuse ORCHESTRATOR_DEBUG=true"
    assert "ORCHESTRATOR_DEBUG" in output


def test_prod_refuses_placeholder_database_password() -> None:
    """The derived database password inherits the component value and is checked."""
    env = _prod_base_env()
    env["ORCHESTRATOR_DATABASE_PASSWORD"] = "change-me"  # pragma: allowlist secret
    returncode, output = _run_manage_check(env)
    assert returncode != 0, "prod boot must refuse the placeholder database password"
    assert "ORCHESTRATOR_DATABASE_PASSWORD" in output


def test_prod_refuses_loopback_only_allowed_hosts() -> None:
    """Loopback-only ALLOWED_HOSTS is the localhost placeholder in disguise.

    Loopback entries are legitimate (the container's own health probe requests
    127.0.0.1 — MT-1.1-05), but prod must still demand a real serving
    hostname (Section 16.2).
    """
    env = _prod_base_env()
    env["ORCHESTRATOR_ALLOWED_HOSTS"] = "localhost,127.0.0.1"
    returncode, output = _run_manage_check(env)
    assert returncode != 0, "prod boot must refuse a loopback-only ALLOWED_HOSTS"
    assert "ORCHESTRATOR_ALLOWED_HOSTS" in output


def test_prod_boots_with_loopback_plus_real_hosts() -> None:
    """Loopback kept for the health probe alongside a real serving hostname."""
    env = _prod_base_env()
    env["ORCHESTRATOR_ALLOWED_HOSTS"] = "127.0.0.1,orchestrator.example.internal"
    returncode, output = _run_manage_check(env)
    assert returncode == 0, f"prod boot with loopback + real host failed:\n{output}"
