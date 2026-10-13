"""Description provider interface — disabled by default (Section 9.5, Section 22 OQ-07; MT-1.12-06).

Section 9.5: *"**Description provider:** pluggable interface with
implementations 'disabled', 'Anthropic-compatible vision model' and
'local model' … failures degrade to OCR-only."* Section 22 records
OQ-07's default: **disabled** (deferred to M1 — enabling a vision model
is an owner decision, not this WP's).

WP-1.12 implements the **interface and the disabled implementation
only** — the two real providers are WP-1.13's deliverable (MT-1.12-02
out-of-scope: "no dependency on WP-1.13 code"). The image stage calls
the provider for its layout caption; with the default it receives ``""``
and completes OCR-only, proving the degradation path exists today.

A configured-but-unimplemented provider **fails fast** with a pointer to
WP-1.13 (Section 9.10) — never a silent caption-less success that
pretends to be enabled.
"""

from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

#: The Section 22 / OQ-07 default, and the only implementation in v1.
SUPPORTED_DESCRIPTION_PROVIDERS: Final[frozenset[str]] = frozenset({"disabled"})


@runtime_checkable
class DescriptionProvider(Protocol):
    """Generate a layout caption for an image (Section 9.5 stage 2)."""

    name: str

    def describe(self, *, image_png: bytes, ocr_text: str) -> str:
        """Return the caption, or ``""`` when this provider produces none.

        Implementations treat the image and transcript as **data**
        (P10) and may raise; callers degrade failures to OCR-only
        (Section 9.5) rather than failing the pipeline.
        """
        ...


class DisabledDescriptionProvider:
    """The Section 22 default: no captions, OCR-only processing."""

    name = "disabled"

    def describe(self, *, image_png: bytes, ocr_text: str) -> str:
        """Always ``""`` — WP-1.13 lights the real providers up."""
        return ""


def get_description_provider() -> DescriptionProvider:
    """The configured provider, fail-fast on unimplemented names (9.10)."""
    name = settings.DESCRIPTION_PROVIDER
    if name == "disabled":
        return DisabledDescriptionProvider()
    raise ImproperlyConfigured(
        f"ORCHESTRATOR_DESCRIPTION_PROVIDER={name!r} is not implemented yet: "
        "vision providers land with WP-1.13 (Section 22 OQ-07 default is "
        "'disabled'; no provider is invented before that decision)."
    )


__all__ = [
    "SUPPORTED_DESCRIPTION_PROVIDERS",
    "DescriptionProvider",
    "DisabledDescriptionProvider",
    "get_description_provider",
]
