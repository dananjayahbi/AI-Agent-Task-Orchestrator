"""Shared fixtures for the bridge test suite (parent plan Section 20.4; MT-2.1-01).

Bridge tests are hermetic: ambient ``ORCHESTRATOR_*`` variables (a developer shell,
a Compose env file) must never leak into config-precedence or logging tests, and
the correlation scope must never bleed between tests (added with MT-2.1-03).

:data:`MINIMAL_MANIFEST` and :func:`write_manifest` (MT-2.2-01…03) give every
binding test the same hand-written known-good manifest — the smallest document
that satisfies ``schemas/manifest.v1.json`` — instead of hand-rolling JSON per file.
"""

from __future__ import annotations

import json
import logging as std_logging
import os
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

import pytest

from orchestrator_bridge import correlation

#: The plan Section 10.3 example values — hand-written known-good fixture.
MINIMAL_MANIFEST: dict[str, object] = {
    "schema_version": 1,
    "project_id": "PID00007",
    "project_name": "Tea Factory ERP",
    "orchestrator_api": "http://localhost:8000/api/v1",
    "default_branch": "main",
    "auto_branch_prefix": "feat/PID00007-",
    "audit_required_default": True,
}

#: Never a real secret — fixture-only token for binding/redaction tests.
FIXTURE_TOKEN = "fixture-token-not-a-real-secret"


@pytest.fixture
def minimal_manifest() -> dict[str, object]:
    """A fresh copy of the hand-written known-good manifest (Section 10.3 example)."""
    return dict(MINIMAL_MANIFEST)


@pytest.fixture
def write_manifest() -> Callable[..., Path]:
    """Write ``orchestrator.json`` (minimal or overridden) into a directory tree."""

    def _write(
        directory: Path,
        document: Mapping[str, object] | None = None,
        *,
        name: str = "orchestrator.json",
    ) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        payload = dict(MINIMAL_MANIFEST if document is None else document)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return _write


@pytest.fixture(autouse=True)
def _hermetic_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip every ambient ``ORCHESTRATOR_*`` variable for one test."""
    for name in [name for name in os.environ if name.startswith("ORCHESTRATOR_")]:
        monkeypatch.delenv(name, raising=False)
    yield


@pytest.fixture(autouse=True)
def _isolated_correlation_scope() -> Iterator[None]:
    """Install an empty correlation scope; restore the outer one afterwards (MT-2.1-03)."""
    token = correlation.set_correlation_id("")
    yield
    correlation.reset_correlation_id(token)


@pytest.fixture(autouse=True)
def _reset_bridge_logging() -> Iterator[None]:
    """Leave no bridge handlers/levels behind after a logging test (MT-2.1-03)."""
    yield
    logger = std_logging.getLogger("bridge")
    logger.handlers.clear()
    logger.setLevel(std_logging.NOTSET)
    logger.propagate = True
