"""View surface of the projects app (Section 9.2).

Split per endpoint group (projects CRUD / policy / manifest); every view
stays a thin adapter over ``apps.projects.services`` — business logic never
lives here (MT-1.3-03, MT-1.3-04, MT-1.3-05).
"""

from __future__ import annotations

from .manifest import ProjectManifestView
from .policy import ProjectPolicyDetailView
from .projects import ProjectDetailView, ProjectListCreateView

__all__ = [
    "ProjectDetailView",
    "ProjectListCreateView",
    "ProjectManifestView",
    "ProjectPolicyDetailView",
]
