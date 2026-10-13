"""Description provider interface, disabled implementation and selector
(Section 9.5; G-14; Section 22 OQ-07; MT-1.13-01/02).

Section 9.5: *"**Description provider:** pluggable interface with
implementations 'disabled', 'Anthropic-compatible vision model' and
'local model' … Descriptions are generated once and cached. Cost and
failures are logged; failures degrade to OCR-only."* G-14 resolved the
spec gap the same way: a pluggable ``DescriptionProvider`` configured in
the backend, can be disabled, result cached permanently per attachment.

WP-1.13 lights the seam WP-1.12 left in place up:

* **Interface** (MT-1.13-01) — input contract: the attachment's
  identity plus the normalized PNG and OCR transcript (Section 9.5
  stage 2 inputs); output contract: caption text or the explicit
  **no-description** result ``""`` (never ``None``, never a fabricated
  placeholder); failure contract: the typed
  :class:`DescriptionProviderError` the pipeline catches to degrade —
  no other exception is a provider failure (a programming error must
  surface, MT-1.13-05 risk note).
* **Disabled** (MT-1.13-02) — the OQ-07 recorded default and the
  out-of-the-box configuration of the whole system: answers the
  interface with ``""`` and makes **no network or subprocess calls of
  any kind**. A deployment without vision credentials or budget
  processes attachments exactly as WP-1.12 allows (OCR-only).
* **Selector** — configuration-driven (``ORCHESTRATOR_DESCRIPTION_
  PROVIDER``, Section 9.10), unknown names fail fast with the supported
  set. ``anthropic-vision`` constructs the remote provider
  (MT-1.13-03), which re-validates its own settings at the point of
  use; the *startup* fail-fast for a selected-but-unconfigured remote
  provider lives with the settings group in
  ``apps.core.settings.base`` (Section 9.10). The ``local model``
  implementation named in Section 9.5 stays unimplemented until a new
  OQ or plan amendment asks for it (WP-1.13 deliverables list only
  disabled and remote-vision; MT-1.13-01 out-of-scope).

Obligations later micro-tasks own, recorded here so they cannot be
missed: cost and failure logging (MT-1.13-03), permanent
per-attachment caching (MT-1.13-04 — see :mod:`apps.attachments.caption`),
degradation to OCR-only on the typed failure (MT-1.13-05 — the
pipeline's caption step).

**Sensitive content** (Section 12.4; WP hard rule): the image bytes and
OCR transcript are attachment content — this module and its
implementations never log them; only identifiers, durations and usage
figures may be reported.
"""

from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#: Every implementation name ``ORCHESTRATOR_DESCRIPTION_PROVIDER``
#: answers to today (Section 9.10 selector; fail-fast on anything else).
SUPPORTED_DESCRIPTION_PROVIDERS: Final[frozenset[str]] = frozenset({"disabled", "anthropic-vision"})


class DescriptionProviderError(Exception):
    """The typed provider-side failure signal (MT-1.13-01 contract).

    Raised only for provider trouble — transport failure, non-2xx
    response, malformed output, missing configuration at the point of
    use. ``reason`` is composed by the raising site from identifiers,
    status codes and exception **type names** — never from provider
    response bodies or attachment content (Section 12.4). ``transient``
    records whether a retry could plausibly succeed; the pipeline
    degrades to OCR-only either way (MT-1.13-05) — the flag feeds
    logging, never attachment failure.
    """

    def __init__(self, reason: str, *, transient: bool = True) -> None:
        super().__init__(reason)
        self.reason = reason
        self.transient = transient


@runtime_checkable
class DescriptionProvider(Protocol):
    """Generate a layout caption for an image (Section 9.5 stage 2)."""

    name: str

    def describe(self, *, attachment_id: str, image_png: bytes, ocr_text: str) -> str:
        """Return the caption, or ``""`` — the explicit no-description.

        ``attachment_id`` is the cache key's owner (G-14: generated
        once *per attachment*); ``image_png`` is the Section 9.5 stage-2
        normalized image; ``ocr_text`` is the transcript providers may
        use as grounding. Both are **data** (P10) — never instructions.

        Implementations may raise :class:`DescriptionProviderError`;
        callers degrade that failure to OCR-only (Section 9.5) rather
        than failing the pipeline.
        """
        ...


class DisabledDescriptionProvider:
    """The OQ-07 recorded default: no captions, OCR-only processing.

    The out-of-the-box configuration of the whole system (G-14 "can be
    disabled"): performs **zero external calls** — no HTTP client, no
    subprocess, no file I/O — and answers every request with the
    explicit no-description result ``""`` (the interface's
    no-description sentinel; the cache treats it as "nothing to cache",
    MT-1.13-04).
    """

    name = "disabled"

    def describe(self, *, attachment_id: str, image_png: bytes, ocr_text: str) -> str:
        """Always ``""`` — a choice, never a failure (MT-1.13-02)."""
        return ""


#: Test/programmatic override seam — the ``set_ocr_engine`` idiom
#: (apps.attachments.ocr), so hermetic suites can install a recording or
#: failing provider without touching configuration.
_provider_override: DescriptionProvider | None = None


def set_description_provider(provider: DescriptionProvider | None) -> None:
    """Install (or clear with ``None``) a programmatic provider override.

    The WP-1.13/1.14 suites use it to install recording and failing
    providers; every suite must clear it again (autouse fixture) so the
    configuration path stays under test elsewhere.
    """
    global _provider_override
    _provider_override = provider


def get_description_provider() -> DescriptionProvider:
    """The configured provider instance (Section 9.10 selector, fail-fast)."""
    if _provider_override is not None:
        return _provider_override
    name = settings.DESCRIPTION_PROVIDER
    if name == "disabled":
        return DisabledDescriptionProvider()
    if name == "anthropic-vision":
        from .description_remote import RemoteVisionDescriptionProvider

        return RemoteVisionDescriptionProvider()
    raise ImproperlyConfigured(
        f"Unknown ORCHESTRATOR_DESCRIPTION_PROVIDER {name!r}; "
        f"supported: {sorted(SUPPORTED_DESCRIPTION_PROVIDERS)} "
        "(Section 9.5 pluggable interface; the Section 9.5 'local model' "
        "implementation is not delivered by WP-1.13 — OQ-07 records only "
        "disabled and the Anthropic-compatible vision model)."
    )


__all__ = [
    "SUPPORTED_DESCRIPTION_PROVIDERS",
    "DescriptionProvider",
    "DescriptionProviderError",
    "DisabledDescriptionProvider",
    "get_description_provider",
    "set_description_provider",
]
