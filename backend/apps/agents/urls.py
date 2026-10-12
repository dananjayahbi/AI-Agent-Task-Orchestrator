"""URL surface of the agents app — ``/api/v1``-prefixed by the root include.

The Section 9.2 Sessions row verbatim: ``POST /agent-sessions`` and
``POST /agent-sessions/{id}/end`` (caller Bridge) — no trailing slashes,
the convention the accounts/projects/tasks surfaces fixed. The Owner-facing
session list (MT-4.9-01) joins when the plan defines its read contract.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import AgentSessionEndView, AgentSessionOpenView

urlpatterns: list[URLPattern] = [
    path("agent-sessions", AgentSessionOpenView.as_view(), name="agent-session-open"),
    path(
        "agent-sessions/<str:id>/end",
        AgentSessionEndView.as_view(),
        name="agent-session-end",
    ),
]
