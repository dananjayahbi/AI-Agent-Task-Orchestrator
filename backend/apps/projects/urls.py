"""URL surface of the projects app — ``/api/v1``-prefixed by the root router.

Paths mirror the Section 9.2 Projects row verbatim (``/projects``,
``/projects/{pid}``, ``/projects/{pid}/policy``,
``/projects/{pid}/manifest``) — no trailing slashes (the accounts surface
fixed that convention in WP-1.2). The manifest route joins with MT-1.3-05.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import (
    ProjectDetailView,
    ProjectListCreateView,
    ProjectManifestView,
    ProjectPolicyDetailView,
)

urlpatterns: list[URLPattern] = [
    path("projects", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<str:pid>", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<str:pid>/policy",
        ProjectPolicyDetailView.as_view(),
        name="project-policy",
    ),
    path(
        "projects/<str:pid>/manifest",
        ProjectManifestView.as_view(),
        name="project-manifest",
    ),
]
