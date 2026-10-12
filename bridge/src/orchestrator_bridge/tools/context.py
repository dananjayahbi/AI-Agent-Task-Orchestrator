"""``get_project_context`` (parent plan Sections 10.3 step 5, 10.5; MT-2.4-06).

Cheap orientation: answers from the session's Section 10.3 cache with **zero
backend calls** once populated — that is what makes it cheap. The payload is
the cached set (project name, rules, policy summary) plus the bound project
id; nothing else (Section 10.5 "compact", Section 12.4).

Miss path (a session resumed without a cache — future HTTP mode): fetch once
through the client via the shared
:func:`~orchestrator_bridge.session.fetch_project_context` and serve from the
refreshed cache. A backend failure surfaces as the client's typed error,
translated at the tool boundary into a structured retryable failure
(Section 10.10). The policy summary is the backend's own structured fields —
no policy logic is re-derived here (Section 19.3). Stale-after-policy-edit
invalidation is unspecified by the plan (OQ recorded in the WP changelog).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..api_errors import ApiError
from ..error_translation import translate_error
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["get_project_context", "make_handler"]


def get_project_context(runtime: ToolRuntime) -> dict[str, Any]:
    """The cached orientation payload: name, rules, policy summary."""
    try:
        context = runtime.project_context()
    except ApiError as exc:
        raise ToolFailure(translate_error(exc)) from None
    return {
        "project_id": context.project_id,
        "project_name": context.name,
        "rules": context.rules,
        "policy_summary": dict(context.policy_summary),
    }


def make_handler(runtime: ToolRuntime) -> Callable[[], dict[str, Any]]:
    """The registered MCP handler: no inputs, bound session (Section 10.5)."""

    def get_project_context_tool() -> dict[str, Any]:
        """Bound project's name, rules and policy summary from the cache."""
        return get_project_context(runtime)

    return get_project_context_tool
