"""Model surface of the tasks app (Section 9.1).

Re-exports every model so the rest of the codebase imports from
``apps.tasks.models`` — the file-per-entity layout stays an internal
concern (MT-1.4-01: ``models/task.py``; MT-1.4-05 adds
``models/dependencies.py``; MT-1.5-05 adds ``models/transitions.py``).
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
from .transitions import ActorType, TaskTransition, TransitionReason

__all__ = [
    "ActorType",
    "ClaimedRole",
    "MergeStatus",
    "ReviewReason",
    "Task",
    "TaskDependency",
    "TaskPriority",
    "TaskState",
    "TaskTransition",
    "TransitionReason",
]
