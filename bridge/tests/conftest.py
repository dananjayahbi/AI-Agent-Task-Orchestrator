"""Shared fixtures for the bridge test suite (parent plan Section 20.4; MT-2.1-01).

Bridge tests are hermetic: ambient ``ORCHESTRATOR_*`` variables (a developer shell,
a Compose env file) must never leak into config-precedence or logging tests, and
the correlation scope must never bleed between tests (added with MT-2.1-03).
"""

from __future__ import annotations

import logging as std_logging
import os
from collections.abc import Iterator

import pytest

from orchestrator_bridge import correlation


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
