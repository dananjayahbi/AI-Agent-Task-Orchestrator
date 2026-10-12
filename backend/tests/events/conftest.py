"""Fixtures shared by the WP-1.9 event suites (this package only).

The production publisher pools a real Redis client lazily; tests swap it
for :class:`FakeRedis` so publish assertions run without services
(Section 18's unit layer) and outage behavior can be forced on demand.
"""

from __future__ import annotations

import pytest

from apps.events import publisher


class FakeRedis:
    """Stand-in for the pooled client: records publishes, can be failed."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []
        self.fail = False

    def publish(self, channel: str, message: str) -> None:
        """Record one publish — or raise when the test has failed the link."""
        if self.fail:
            raise ConnectionError("redis is down (test outage)")
        self.messages.append((channel, message))


@pytest.fixture
def fake_publisher(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    """Route post-commit publishes into an in-process recorder."""
    client = FakeRedis()
    monkeypatch.setattr(publisher, "_client", client)
    return client
