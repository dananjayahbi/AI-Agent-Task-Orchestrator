"""Attachments-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

The envelope handler (``apps/core/exceptions.py``) passes any DRF
``APIException`` whose ``default_code`` is already canonical straight
through, so these classes never invent a code — they name one that
exists in the closed 19-code catalog and choose the HTTP status the
OpenAPI contract documents for the attachments endpoints.

Status decisions (recorded in the WP changelog):

* ``ATTACHMENT_UNSUPPORTED_FORMAT`` → **415**: the semantically exact
  status for a content-sniffed type rejection (Section 9.5); the code
  stays the catalog contract, the status is this endpoint's documented
  choice (error-envelope.md: status mapping lives in the OpenAPI
  contract).
* Oversize / over-count / over-total reuse DRF's ``ValidationError`` →
  **400** ``VALIDATION_ERROR`` (the envelope handler's documented
  mapping) with structured ``details`` — no new class needed.
* Deletion of a completed/archived task's attachment reuses the tasks
  domain's **409** ``TASK_STATE_CONFLICT`` semantics through
  :class:`AttachmentOnImmutableTask` (Section 16.3: the user never
  hard-deletes there; the retention path owns it).
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import ATTACHMENT_UNSUPPORTED_FORMAT, TASK_STATE_CONFLICT


class AttachmentUnsupportedFormat(APIException):
    """Content sniffing refused the file (Section 9.5; FR-ATT-01).

    Raised when the sniffed type is not in the Section 9.5 allowlist, or
    the declared multipart type contradicts the sniffed one — extension
    alone never decides, and a mismatch is rejected (MT-1.11-02).
    """

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_code = ATTACHMENT_UNSUPPORTED_FORMAT
    default_detail = "The file content does not match an allowed attachment type."


class AttachmentOnImmutableTask(APIException):
    """DELETE refused: the task is completed or archived (Section 16.3).

    Section 16.3 fixes "deletion is by retention job, never by user
    action on completed tasks" — the API resolves the Section 9.2
    ``DELETE`` vs that rule conservatively (MT-1.11-05 risk note): the
    caller is told the retention path owns the bytes now, in a 409 with
    the canonical ``TASK_STATE_CONFLICT`` code.
    """

    status_code = status.HTTP_409_CONFLICT
    default_code = TASK_STATE_CONFLICT
    default_detail = (
        "Attachments of completed or archived tasks are retained until the "
        "archive grace period ends; they cannot be deleted through the API."
    )


__all__ = ["AttachmentOnImmutableTask", "AttachmentUnsupportedFormat"]
