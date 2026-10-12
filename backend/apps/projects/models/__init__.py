"""Model surface of the projects app (Section 9.1).

Re-exports every model so the rest of the codebase imports from
``apps.projects.models`` — the file-per-entity layout stays an internal
concern (MT-1.3-02: ``models/project.py`` and ``models/policy.py``, one
entity per file).
"""

from __future__ import annotations

from .policy import LeaseExtensionMode, MergeStrategy, ProjectPolicy
from .project import ActiveStatus, Project

__all__ = [
    "ActiveStatus",
    "LeaseExtensionMode",
    "MergeStrategy",
    "Project",
    "ProjectPolicy",
]
