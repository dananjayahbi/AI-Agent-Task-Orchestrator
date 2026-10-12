"""URL surface of the leases app — ``/api/v1``-prefixed by the root include.

The Section 9.2 "Agent work" row verbatim: ``POST /tasks/{id}/claim``,
``POST /tasks/{id}/release`` and ``GET /projects/{pid}/work`` — no
trailing slashes (the convention the other surfaces fixed). Views live
in this app (Section 9.1: ``leases`` owns claim, extend, release,
sweep, fencing); the routes are grouped here so the WP's surface stays
in one owned file.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import ClaimView, ReleaseView, WorkView

urlpatterns: list[URLPattern] = [
    path("tasks/<str:id>/claim", ClaimView.as_view(), name="task-claim"),
    path("tasks/<str:id>/release", ReleaseView.as_view(), name="task-release"),
    path("projects/<str:pid>/work", WorkView.as_view(), name="project-work"),
]
