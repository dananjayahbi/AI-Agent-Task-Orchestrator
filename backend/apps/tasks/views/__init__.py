"""View surface of the tasks app (Section 9.2).

Split per endpoint group (task CRUD now; list/filters joins with
MT-1.4-04; the Progress-row checkpoint route with MT-1.8-03/04); every
view stays a thin adapter over ``apps.tasks.services`` — business logic
never lives here (MT-1.4-03).
"""

from __future__ import annotations

from .checkpoints import CheckpointListCreateView
from .tasks import TaskDetailView, TaskListCreateView

__all__ = ["CheckpointListCreateView", "TaskDetailView", "TaskListCreateView"]
