"""Serializer surface of the tasks app (Section 9.2).

One module per contract family (MT-1.4-03: task CRUD shapes; MT-1.4-04
adds the list envelope/query shapes alongside).
"""

from __future__ import annotations

from .tasks import (
    EDITABLE_FIELDS,
    TaskCreateSerializer,
    TaskListEnvelopeSerializer,
    TaskListQuerySerializer,
    TaskSerializer,
    TaskUpdateSerializer,
)

__all__ = [
    "EDITABLE_FIELDS",
    "TaskCreateSerializer",
    "TaskListEnvelopeSerializer",
    "TaskListQuerySerializer",
    "TaskSerializer",
    "TaskUpdateSerializer",
]
