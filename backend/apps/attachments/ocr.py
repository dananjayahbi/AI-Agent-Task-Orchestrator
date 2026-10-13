"""Pluggable OCR engine interface (Sections 6.6, 9.5 stage 2, 9.10; MT-1.12-02).

Section 6.6 fixes the shape: *"Tesseract-based default behind a
pluggable interface — local and free; replaceable by vision-model
OCR."* This module is that interface:

* :class:`OcrEngine` — the protocol every engine satisfies:
  image bytes in, transcript text out.
* :class:`TesseractOcrEngine` — the default, a subprocess over the
  ``tesseract`` CLI (``ORCHESTRATOR_OCR_TESSERACT_CMD``, default
  ``tesseract`` on PATH). No Python binding, so the engine swap never
  touches requirements; a missing binary is an explicit, human-readable
  failure — never a silent empty transcript.
* :func:`get_ocr_engine` / :func:`set_ocr_engine` — the selection seam
  driven by ``ORCHESTRATOR_OCR_ENGINE`` (default ``tesseract``),
  fail-fast on unknown names (Section 9.10), with a test-only override
  hook so suites run hermetically where the binary is absent (the real
  path is exercised wherever Tesseract exists — marked, not weakened).

**Sensitive content** (Section 12.4; WP hard rule): transcripts are
attachment content — this module never logs them; only sizes, exit
codes and durations may be reported.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Final, Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .errors import PermanentPipelineError, TransientPipelineError

#: The engine names Section 6.6's configuration accepts today.
SUPPORTED_ENGINES: Final[frozenset[str]] = frozenset({"tesseract"})

#: Per-page OCR wall-clock budget — a hung engine must not hold the
#: worker forever (Section 12.1 in-process limits; documented default,
#: re-tries as transient when it trips).
OCR_TIMEOUT_SECONDS: Final = 30


@runtime_checkable
class OcrEngine(Protocol):
    """The Section 6.6 pluggable OCR interface."""

    name: str

    def recognize(self, image: bytes, *, mime_type: str) -> str:
        """Return the transcript of *image* (UTF-8 text, may be empty).

        Raises :class:`TransientPipelineError` for retryable engine
        trouble (timeout, non-zero exit) and
        :class:`PermanentPipelineError` when the engine cannot run at
        all (binary missing — configuration, not contention).
        """
        ...


class TesseractOcrEngine:
    """The Section 6.6 default engine over the ``tesseract`` CLI."""

    name = "tesseract"

    def __init__(self, command: str | None = None) -> None:
        self._command = command if command is not None else settings.OCR_TESSERACT_CMD

    def available(self) -> bool:
        """Whether the configured executable resolves on this host."""
        return shutil.which(self._command) is not None

    def recognize(self, image: bytes, *, mime_type: str) -> str:
        """Run tesseract over *image* bytes (stdin → stdout, eng)."""
        if not self.available():
            raise PermanentPipelineError(
                f"OCR engine 'tesseract' is configured but the executable "
                f"{self._command!r} was not found on PATH "
                "(ORCHESTRATOR_OCR_TESSERACT_CMD; Section 6.6 default engine)."
            )
        try:
            completed = subprocess.run(
                [self._command, "stdin", "stdout"],
                input=image,
                capture_output=True,
                timeout=OCR_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TransientPipelineError(
                f"OCR engine timed out after {OCR_TIMEOUT_SECONDS}s on one page "
                "(transient; retried with backoff — Section 9.9)."
            ) from exc
        except OSError as exc:
            raise TransientPipelineError(
                "OCR engine could not be executed (transient I/O failure)."
            ) from exc
        if completed.returncode != 0:
            raise TransientPipelineError(
                f"OCR engine exited with code {completed.returncode} "
                "(transient; retried with backoff — Section 9.9)."
            )
        # stderr intentionally dropped: tesseract chatter can quote image
        # content, and extracted text never reaches logs (Section 12.4).
        return completed.stdout.decode("utf-8", errors="replace").strip()


_engine_override: OcrEngine | None = None


def set_ocr_engine(engine: OcrEngine | None) -> None:
    """Install (or clear with ``None``) a test/programmatic engine override.

    The WP suites use this to run hermetically where Tesseract is not
    installed; unit tests that prove real recognition skip only when the
    binary is genuinely absent (MT-1.12-02/08 honest-marking rule).
    """
    global _engine_override
    _engine_override = engine


def get_ocr_engine() -> OcrEngine:
    """The configured engine instance (Section 9.10 selector, fail-fast)."""
    if _engine_override is not None:
        return _engine_override
    name = settings.OCR_ENGINE
    if name == "tesseract":
        return TesseractOcrEngine()
    raise ImproperlyConfigured(
        f"Unknown ORCHESTRATOR_OCR_ENGINE {name!r}; "
        f"supported: {sorted(SUPPORTED_ENGINES)} (Section 6.6 pluggable interface)."
    )


def tesseract_available() -> bool:
    """Whether the default engine can run on this host (test marking)."""
    return TesseractOcrEngine().available()


__all__ = [
    "OCR_TIMEOUT_SECONDS",
    "SUPPORTED_ENGINES",
    "OcrEngine",
    "TesseractOcrEngine",
    "get_ocr_engine",
    "set_ocr_engine",
    "tesseract_available",
]
