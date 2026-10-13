"""Serializer surface of the tasks app (Section 9.2).

One module per contract family (MT-1.4-03: task CRUD shapes; MT-1.4-04
adds the list envelope/query shapes alongside; MT-1.8-03/04 add the
Progress-row checkpoint shapes).
"""

from __future__ import annotations

from .checkpoints import (
    CheckpointCreateSerializer,
    CheckpointListEnvelopeSerializer,
    CheckpointListQuerySerializer,
    CheckpointSerializer,
    CheckpointWriteResponseSerializer,
    checkpoint_payload,
)
from .resolutions import (
    ResolutionListEnvelopeSerializer,
    ResolutionListQuerySerializer,
    ResolutionPatchSerializer,
    ResolutionSerializer,
    ResolutionSubmitSerializer,
    ResolutionWriteResponseSerializer,
    resolution_payload,
    task_state_payload,
)
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
    "CheckpointCreateSerializer",
    "CheckpointListEnvelopeSerializer",
    "CheckpointListQuerySerializer",
    "CheckpointSerializer",
    "CheckpointWriteResponseSerializer",
    "ResolutionListEnvelopeSerializer",
    "ResolutionListQuerySerializer",
    "ResolutionPatchSerializer",
    "ResolutionSerializer",
    "ResolutionSubmitSerializer",
    "ResolutionWriteResponseSerializer",
    "TaskCreateSerializer",
    "TaskListEnvelopeSerializer",
    "TaskListQuerySerializer",
    "TaskSerializer",
    "TaskUpdateSerializer",
    "checkpoint_payload",
    "resolution_payload",
    "task_state_payload",
]
