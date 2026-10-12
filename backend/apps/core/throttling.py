"""API-side rate limiting (Section 9.1: ``core`` owns rate limiting; FR-SEC-05).

Scope rule (MT-1.2-06): throttling applies to the Section 9.2 endpoints whose
caller column is Agent / Auditor / Bridge / Mobile — *not* to the Owner's web
endpoints, which FR-SEC-05 does not cover. Views opt in by naming a class in
``throttle_classes``; the two classes here cover today's device endpoints, and
agent-facing endpoints (``/projects/{pid}/work``, claim, checkpoint,
resolution, verdict, merge, agent-sessions — WP-1.4/1.5/1.6/2.x/3.x) name
``AgentEndpointThrottle`` when they land. The endpoint-coverage test in
``tests/test_rate_limiting.py`` enumerates the Section 9.2 rows and fails the
moment a not-yet-implemented route appears without its throttle, so the rule
cannot be forgotten ("by endpoint class, not by a frozen list").

Keying (Section 12.3 layered intent; MT-1.2-06 risk note): the budget is
per **authenticated token id** — two sessions or two agents never share a
budget, and revoking a token frees its key. Unauthenticated callers fall back
to the client address. Limits and windows come from the Section 9.10
``ORCHESTRATOR_RATE_LIMIT_<SCOPE>_PER_MINUTE`` settings via
``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`` — no magic numbers here.

Exceeding a budget raises DRF's ``Throttled``, which the envelope handler
maps to the catalog's ``RATE_LIMITED`` (429, ``retryable: true`` — see
``apps/core/exceptions.py``).
"""

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ImproperlyConfigured
from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class TokenKeyedRateThrottle(SimpleRateThrottle):
    """Base throttle: per-token budget, per-address fallback.

    Subclasses only set :attr:`scope`, which must exist in
    ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`` (declared in
    ``settings/base.py`` from the canonical ``ORCHESTRATOR_RATE_LIMIT_*``
    environment names — configuration.md).
    """

    scope = ""

    def get_rate(self) -> str | None:
        """Read the configured rate dynamically.

        ``SimpleRateThrottle`` binds ``THROTTLE_RATES`` once at import time;
        re-reading ``api_settings`` here keeps the throttle honest under
        ``settings`` overrides in tests (DRF reloads ``api_settings`` on the
        ``setting_changed`` signal) and under any future runtime reload.
        """
        if not self.scope:
            raise ImproperlyConfigured(
                f"You must set `.scope` or `.rate` for {self.__class__.__name__} throttle."
            )
        try:
            # The stubs type this dict ``float | int | None``; every runtime
            # value is the documented ``"<n>/<unit>"`` string (settings/base.py).
            rate = cast(str, api_settings.DEFAULT_THROTTLE_RATES[self.scope])
        except KeyError as exc:
            raise ImproperlyConfigured(
                f"No default throttle rate set for {self.scope!r} scope."
            ) from exc
        return rate

    def get_cache_key(self, request: Request, view: Any) -> str | None:
        """Token id when authenticated, client address otherwise."""
        token_pk = getattr(request.auth, "pk", None)
        ident = f"token:{token_pk}" if token_pk is not None else f"addr:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AgentEndpointThrottle(TokenKeyedRateThrottle):
    """Agent-facing endpoints (Section 9.2 callers: Agent, Auditor, Bridge).

    Every such endpoint names this class in ``throttle_classes`` as it lands
    (WP-1.4/1.5/1.6 for work/claim/checkpoint/resolution/verdict, WP-2.x for
    agent-sessions, WP-3.x for the merge queue); the coverage test in
    ``tests/test_rate_limiting.py`` enumerates those Section 9.2 rows and
    forces the wiring.
    """

    scope = "agent"


class DeviceEndpointThrottle(TokenKeyedRateThrottle):
    """Mobile device endpoints (Section 9.2 Devices row; FR-SEC-05)."""

    scope = "device"
