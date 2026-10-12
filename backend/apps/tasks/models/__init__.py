"""Model surface of the tasks app (Section 9.1).

Re-exports every model so the rest of the codebase imports from
``apps.tasks.models`` — the file-per-entity layout stays an internal
concern (MT-1.4-01: ``models/task.py``; MT-1.4-05 adds
``models/dependencies.py``, one entity per file).
"""

from __future__ import annotations

from .dependencies import TaskDependency
from .task import (
    ClaimedRole,
    MergeStatus,
    ReviewReason,
    Task,
    TaskPriority,
    TaskState,
)

__all__ = [
    "ClaimedRole",
    "MergeStatus",
    "ReviewReason",
    "Task",
    "TaskDependency",
    "TaskPriority",
    "TaskState",
]
