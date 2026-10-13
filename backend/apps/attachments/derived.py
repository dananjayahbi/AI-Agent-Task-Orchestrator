"""Derived-artifact registry and cleanup (Section 9.5 "derived data is re-creatable"; MT-1.12-02).

Pipeline-derived blobs that live in the storage abstraction under
:func:`apps.attachments.storage.derived_key` (per-attachment namespace,
so no reference counting — storage.py's recorded design). Every artifact
has exactly one registered name; adding an artifact means registering it
here so the deletion and retention paths keep their promise of leaving
no orphaned bytes (MT-1.11-05's cleanup discipline extends to derived
data).
"""

from __future__ import annotations

from typing import Final

from .models import TaskAttachment
from .storage import derived_key, get_storage

#: The Section 9.5 stage-2 normalized image (long edge capped, metadata
#: stripped) — the bytes WP-1.14's ``image_base64`` format serves.
NORMALIZED_IMAGE_NAME: Final = "normalized.png"

#: Every artifact name this application may write — the cleanup list.
DERIVED_ARTIFACT_NAMES: Final[tuple[str, ...]] = (NORMALIZED_IMAGE_NAME,)


def put_derived(attachment_id: str, artifact: str, data: bytes) -> str:
    """Store a derived artifact, **replacing** any previous version.

    ``StorageBackend.put`` is idempotent-no-op for content keys (same
    key means same bytes — MT-1.11-01); derived artifacts are keyed by
    identity, not content, so a re-run after an algorithm change must
    overwrite (Section 9.5: derived data replaced, never duplicated —
    MT-1.12-02). Delete-then-put: the artifact is re-creatable, so the
    tiny non-atomic window is acceptable and self-heals on reprocessing.
    """
    key = derived_key(attachment_id, artifact)
    storage = get_storage()
    storage.delete(key)
    storage.put(key, data)
    return key


def delete_derived_artifacts(attachment: TaskAttachment) -> int:
    """Remove every registered derived artifact of *attachment*.

    Idempotent (absent keys are a no-op) and called from the soft-delete
    path, the retention purge and ``drop_derived_data`` — derived bytes
    never outlive their record's intent to keep them.
    """
    storage = get_storage()
    removed = 0
    for artifact in DERIVED_ARTIFACT_NAMES:
        key = derived_key(str(attachment.pk), artifact)
        if storage.exists(key):
            storage.delete(key)
            removed += 1
    return removed


__all__ = [
    "DERIVED_ARTIFACT_NAMES",
    "NORMALIZED_IMAGE_NAME",
    "delete_derived_artifacts",
    "put_derived",
]
