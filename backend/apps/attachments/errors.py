"""Pipeline failure classification (Sections 9.5 stage 5, 9.9; MT-1.12-01/07).

The worker pipeline reports every failure as one of two classes so the
retry policy has exactly one place to decide (MT-1.12-07 owns that
decision; this module only defines the vocabulary):

* :class:`PermanentPipelineError` — retrying cannot help (bad content,
  integrity mismatch, unsupported type, hostile/malformed input). The
  attachment lands in ``failed`` immediately with the human-readable
  ``reason`` (Section 9.5 stage 5).
* :class:`TransientPipelineError` — plausibly temporary (OCR engine
  timeout, storage I/O, contention). The Celery task retries with
  backoff up to the configured cap (Section 9.9), then lands ``failed``.

**Reasons are ours, never the content's** (Section 12.4; the WP-1.12
hard rule): every reason string is composed by the raising site from
identifiers and stage names — never from extracted text — and is
truncated before storage. Unexpected third-party exceptions are wrapped
with the exception *type name only*, so no snippet of a sensitive
attachment can reach the record, an event or a log.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for attachment-pipeline failures.

    ``reason`` is the human-readable message stored on the record's
    ``failure_detail`` and shown on the descriptor (FR-ATT-07 visible).
    """

    transient = False

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PermanentPipelineError(PipelineError):
    """Deterministic failure: content, integrity or configuration.

    Retrying is pointless, so the task fails the attachment at once
    (Section 9.5 stage 5 — "permanent failures show a human-readable
    reason").
    """

    transient = False


class TransientPipelineError(PipelineError):
    """Plausibly temporary failure: eligible for retry with backoff."""

    transient = True


def describe_exception(exc: BaseException) -> str:
    """A safe one-line reason for an *unexpected* exception.

    Type name only — exception messages from parsers and engines may
    quote input bytes, and extracted text is sensitive (Section 12.4;
    MT-1.12 hard rule "never logged"). The ``from exc`` chain keeps the
    detail available to a debugger attached to the worker, never to the
    stored record.
    """
    return f"unexpected {type(exc).__name__} during attachment processing"


__all__ = [
    "PermanentPipelineError",
    "PipelineError",
    "TransientPipelineError",
    "describe_exception",
]
