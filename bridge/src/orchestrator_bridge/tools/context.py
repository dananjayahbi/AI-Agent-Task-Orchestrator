"""``get_project_context`` (parent plan Sections 10.3 step 5, 10.5; MT-2.4-06,
MT-2.7-02).

Cheap orientation: answers from the session's Section 10.3 cache with **zero
backend calls** once populated — that is what makes it cheap. The payload is
the cached set (project name, rules, policy summary) plus the bound project
id; nothing else (Section 10.5 "compact", Section 12.4).

The ``rules`` field is the **merged Section 10.6 block** (MT-2.7-02): the
coder template plus the cached ``system_prompt_rules`` appended, rendered by
the shared :func:`~orchestrator_bridge.rules.render_session_rules` path —
byte-identical to the initialize-time server instructions for the same
session inputs (G-08 consistency; MT-2.7-02's one-render-path acceptance).
The raw project-rules text alone is no longer surfaced here: the block is
the Section 10.6 artifact agents must follow.

Miss path (a session resumed without a cache — future HTTP mode): fetch once
through the client via the shared
:func:`~orchestrator_bridge.session.fetch_project_context` and serve from the
refreshed cache. A backend failure surfaces as the client's typed error,
translated at the tool boundary into a structured retryable failure
(Section 10.10). The policy summary is the backend's own structured fields —
no policy logic is re-derived here (Section 19.3). Stale-after-owner-edit
invalidation is unspecified by the plan (OQ recorded in the WP changelog).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..api_errors import ApiError
from ..error_translation import translate_error
from ..rules import render_session_rules
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["get_project_context", "make_handler"]


def get_project_context(runtime: ToolRuntime) -> dict[str, Any]:
    """The cached orientation payload: name, merged rules block, policy summary."""
    try:
        context = runtime.project_context()
    except ApiError as exc:
        raise ToolFailure(translate_error(exc)) from None
    return {
        "project_id": context.project_id,
        "project_name": context.name,
        "rules": render_session_rules(
            "coder",
            project_rules=context.rules,
            policy_summary=context.policy_summary,
        ),
        "policy_summary": dict(context.policy_summary),
    }


def make_handler(runtime: ToolRuntime) -> Callable[[], dict[str, Any]]:
    """The registered MCP handler: no inputs, bound session (Section 10.5)."""

    def get_project_context_tool() -> dict[str, Any]:
        """Bound project's name, rules and policy summary from the cache."""
        return get_project_context(runtime)

    return get_project_context_tool
