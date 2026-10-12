"""Fixtures shared by the WP-1.9/WP-1.10 event suites (this package only).

The production publisher pools a real Redis client lazily; tests swap it
for :class:`FakeRedis` so publish assertions run without services
(Section 18's unit layer) and outage behavior can be forced on demand.

WP-1.10 adds the caller credentials the gateway tests need through the
**real** routes (Section 12.2): a logged-in Owner session client, a device
token and an agent token — the same three caller kinds the authorization
matrix exercises, minted per test so revocation/throttle state never bleeds
between tests.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.events import fanout, publisher

PASSWORD = "wp110-stream-tests!"  # pragma: allowlist secret


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


@pytest.fixture(autouse=True)
def isolated_hub(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Unit layer (Section 18): no Redis dial-out, no cross-test leakage.

    The fan-out subscriber is disabled by default — the factory seam
    returns ``None`` (fanout.py's documented test seam, mirroring the
    publisher's ``_client`` patch). A test that needs a subscriber (the
    single-subscription assertion, the delivery load test) re-patches
    ``fanout._async_redis`` with its own fake *within* this same
    ``monkeypatch`` instance, and closes the hub at the end of its
    scenario. Registrations are cleared after every test so one suite's
    connections can never leak into another's counts.
    """
    monkeypatch.setattr(fanout, "_async_redis", lambda: None)
    yield
    fanout.hub._connections.clear()


# --- WP-1.10 caller credentials (Section 12.2 "Read events" row) ------------


@pytest.fixture
def owner_api(db: None) -> APIClient:
    """A logged-in Owner session client (cookie transport) for setup calls."""
    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def device_token(owner_api: APIClient) -> str:
    """A live device bearer token — the Device cell of the matrix."""
    response = owner_api.post(
        "/api/v1/devices",
        {"platform": "android", "push_token": "wp110-device"},
    )
    assert response.status_code == 201, response.content
    token = str(response.json()["token"])
    assert token
    return token


@pytest.fixture
def agent_token(owner_api: APIClient) -> str:
    """A live agent bearer token (PID00001 coder) — must never subscribe."""
    response = owner_api.post(
        "/api/v1/tokens/agent",
        {"project_id": "PID00001", "scopes": ["coder"]},
    )
    assert response.status_code == 201, response.content
    token = str(response.json()["token"])
    assert token
    return token
