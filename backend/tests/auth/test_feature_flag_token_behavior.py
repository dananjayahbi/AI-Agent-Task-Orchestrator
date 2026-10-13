"""MT-1.2-01 follow-up, closed by MT-1.15-04 — token behavior under feature flags.

The follow-up MT-1.15-04 names asks what token verification does when "the
auth feature flag is (re)configured". At M1 the only flag seam that exists is
WP-0.5's ``ORCHESTRATOR_FEATURE_FLAGS`` list (``settings.FEATURE_FLAGS``) —
no authentication code path reads it, and the ``AUTH_MODE=oidc`` value named
across the plan's micro-documents belongs to WP-1.3's OIDC work. Constructing
that matrix requires a real OIDC issuer; MT-1.15-04's risk note forbids
stubbing fake OIDC behavior, so the live-flag matrix is **explicitly deferred
to WP-1.3** (recorded in the WP-1.15 changelog — no silent scope reduction).

What is pinned today is the seam contract: (re)configuring the flag list —
empty, an unrelated entry, or an ``AUTH_MODE=oidc`` value — must never change
issuance or verification of project-scoped agent tokens. When WP-1.3 makes
the flag live it must update this seam deliberately (the same drift-guard
pattern the adopted matrix uses for deferred endpoints).

Run: ``pytest backend/tests/auth/test_feature_flag_token_behavior.py -v``.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import AUTH_REQUIRED, ROLE_NOT_PERMITTED
from tests.attachments import helpers

PASSWORD = "wp115-flag-token-1!"  # pragma: allowlist secret

#: The flag states a reconfiguration can produce: off, an unrelated entry,
#: and the plan-documented OIDC value (inert until WP-1.3).
FLAG_STATES: tuple[tuple[str, ...], ...] = (
    (),
    ("unrelated-experiment",),
    ("AUTH_MODE=oidc",),
)


@pytest.mark.parametrize("flags", FLAG_STATES, ids=lambda state: "+".join(state) or "empty")
def test_reconfiguring_feature_flags_never_alters_token_verification(
    flags: tuple[str, ...], db: None, settings: Any
) -> None:
    """Issuance and verification round-trip identically in every flag state."""
    User.objects.create_user("wp115-flag-owner", None, PASSWORD)
    session = APIClient()
    login = session.post(
        "/api/v1/auth/login", {"username": "wp115-flag-owner", "password": PASSWORD}
    )
    assert login.status_code == 200, login.content

    with override_settings(FEATURE_FLAGS=list(flags)):
        # The override is really in force — otherwise this proves nothing.
        assert list(settings.FEATURE_FLAGS) == list(flags)

        issued = session.post(
            "/api/v1/tokens/agent", {"project_id": "PID00001", "scopes": ["coder"]}
        )
        assert issued.status_code == 201, issued.content
        agent = APIClient()
        agent.credentials(HTTP_AUTHORIZATION=f"Bearer {issued.json()['token']}")

        # Authenticated (the token parses and verifies) but below the row's
        # role: 403 ROLE_NOT_PERMITTED is the authenticated wrong-role shape.
        listed = agent.get("/api/v1/tokens")
        assert listed.status_code == 403, listed.content
        assert helpers.envelope_code(listed) == ROLE_NOT_PERMITTED

        # No credential still fails closed with the catalog code.
        anonymous = APIClient().get("/api/v1/tokens")
        assert anonymous.status_code == 401, anonymous.content
        assert helpers.envelope_code(anonymous) == AUTH_REQUIRED
