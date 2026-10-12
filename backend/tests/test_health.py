"""Tests for the Ops health endpoints (MT-1.1-03; Sections 9.2, 16.1, 17).

Dependency checks are monkeypatched per scenario, so both the success and the
not-ready paths are proven deterministically with no Postgres or Redis present
(the readiness failure of one dependency must not depend on whether some other
dependency happens to be reachable on the test machine).
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.core import health
from apps.core.errors import SERVER_ERROR


def _raise_unreachable() -> None:
    raise OSError("dependency simulated as unreachable")


def _noop() -> None:
    return None


@pytest.fixture
def no_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both dependency checks report reachable."""
    monkeypatch.setattr(health, "check_database", _noop)
    monkeypatch.setattr(health, "check_cache", _noop)


def test_live_returns_success_without_dependency_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /health/live is up regardless of dependencies (Section 9.2 Ops)."""
    monkeypatch.setattr(health, "check_database", _raise_unreachable)
    monkeypatch.setattr(health, "check_cache", _raise_unreachable)

    response = Client().get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_ready_returns_success_when_database_and_cache_are_reachable(
    no_failures: None,
) -> None:
    """GET /health/ready is 200 when the Section 16.1 dependencies answer."""
    response = Client().get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "cache": "ok"},
    }


def test_ready_returns_error_envelope_when_database_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A down database yields non-2xx with a catalog code (Sections 9.2, 20.4.5)."""
    monkeypatch.setattr(health, "check_database", _raise_unreachable)
    monkeypatch.setattr(health, "check_cache", _noop)

    response = Client().get("/health/ready")

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == SERVER_ERROR
    assert error["retryable"] is True
    assert set(error) == {"code", "message", "retryable", "details", "correlation_id"}
    assert isinstance(error["correlation_id"], str) and error["correlation_id"]


def test_ready_returns_error_envelope_when_cache_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A down cache yields the same non-2xx envelope shape."""
    monkeypatch.setattr(health, "check_database", _noop)
    monkeypatch.setattr(health, "check_cache", _raise_unreachable)

    response = Client().get("/health/ready")

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == SERVER_ERROR
    assert error["retryable"] is True
    assert error["correlation_id"]


def test_health_endpoints_need_no_authentication() -> None:
    """Both endpoints answer without user or agent credentials (Section 9.2)."""
    assert Client().get("/health/live").status_code == 200
    assert Client().get("/health/ready").status_code in (200, 503)
