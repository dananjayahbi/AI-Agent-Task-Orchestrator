"""Client capability resolution for attachment reads (Sections 10.4, 10.9; MT-2.5-01; ADR-006).

Every ``read_task_attachment`` call resolves what it may deliver through
Section 10.4's four steps, short-circuiting on the first decisive answer:

1. **explicit format** — a non-``auto`` ``format_preference`` in the call
   wins over everything below (the caller is the authority);
2. **session capability** — the vision/text-only value set at startup
   (``Settings.session_capability`` from
   ``ORCHESTRATOR_BRIDGE_SESSION_CAPABILITY``; Section 10.4 step 2);
3. **client table** — the MCP client's handshake name/version looked up in
   the editable ``bridge/capability_table/`` file (MT-2.5-02);
4. **text-safe default** — ``unknown``: deliver OCR text plus a description,
   with a note on how to request the image explicitly.

The resolver is a **pure function** of explicit inputs — the session value
and the table are parameters, never globals — so the order is unit-testable;
the attachment handler supplies the process-wide table
(:func:`orchestrator_bridge.capability_table.load_capability_table`) and the
runtime's session capability, and reads the client identity off the MCP
handshake context (:func:`client_identity`) when the SDK provides one.

Honesty rules (ADR-006; WP-5 exit criteria; Section 10.9): the resolver
never *infers* vision. ``unknown`` is treated as text-safe, and only a
step-2 operator value or a table entry recorded from a real conformance run
may set ``vision``/``text_only``. Every text-only or unknown path carries a
note telling the model how to request the image explicitly; an explicit
``image_base64`` request is the caller overriding this resolution (the
"forced" path of Section 9.5, gated by the tool's ``force`` input).

The reported ``step`` is whichever step decided the *delivered format*:
``explicit_format`` when step 1 answered, else the capability step
(``session_config`` / ``client_table`` / ``default_text_safe``). The
resolved capability accompanies every answer because Section 9.5's
image gate needs it even under an explicit format.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # pragma: no cover - import cycle guard (table imports the constants)
    from .capability_table import CapabilityTable

__all__ = [
    "ATTACHMENT_FORMATS",
    "CAPABILITIES",
    "CAPABILITY_TEXT_ONLY",
    "CAPABILITY_UNKNOWN",
    "CAPABILITY_VISION",
    "FORMAT_AUTO",
    "FORMAT_IMAGE_BASE64",
    "FORMAT_MARKDOWN",
    "FORMAT_TEXT_OCR",
    "IMAGE_REQUEST_NOTE",
    "CapabilityResolution",
    "ResolutionStep",
    "client_identity",
    "resolve_capability",
]

#: The wire values of ``AttachmentContent.format`` / the tool's
#: ``format_preference`` (Section 9.5 retrieval table; OpenAPI AttachmentContent).
FORMAT_AUTO: Final = "auto"
FORMAT_IMAGE_BASE64: Final = "image_base64"
FORMAT_TEXT_OCR: Final = "text_ocr"
FORMAT_MARKDOWN: Final = "markdown"

#: Every value the tool's ``format_preference`` accepts (schema enum, same order).
ATTACHMENT_FORMATS: Final[tuple[str, ...]] = (
    FORMAT_AUTO,
    FORMAT_IMAGE_BASE64,
    FORMAT_TEXT_OCR,
    FORMAT_MARKDOWN,
)

#: Session/client capabilities (Section 10.9's matrix vocabulary).
CAPABILITY_VISION: Final = "vision"
CAPABILITY_TEXT_ONLY: Final = "text_only"
CAPABILITY_UNKNOWN: Final = "unknown"

#: The closed set a session capability or table entry may carry.
CAPABILITIES: Final[frozenset[str]] = frozenset(
    {CAPABILITY_VISION, CAPABILITY_TEXT_ONLY, CAPABILITY_UNKNOWN}
)

#: The Section 10.4 step-4 note: how to request the image explicitly.
IMAGE_REQUEST_NOTE: Final = (
    "The session's image capability is unknown or text-only, so images arrive as OCR "
    "text plus a description. If the client renders images, request "
    'format_preference="image_base64".'
)


class ResolutionStep(StrEnum):
    """Which Section 10.4 step decided the delivered format."""

    EXPLICIT_FORMAT = "explicit_format"  # step 1
    SESSION_CONFIG = "session_config"  # step 2
    CLIENT_TABLE = "client_table"  # step 3
    DEFAULT_TEXT_SAFE = "default_text_safe"  # step 4


@dataclass(frozen=True, slots=True)
class CapabilityResolution:
    """One attachment read's resolved format behavior and its provenance."""

    format_preference: str
    """The explicit request, or ``auto`` when the resolver is deciding."""

    capability: str
    """Resolved session capability — one of :data:`CAPABILITIES`."""

    step: ResolutionStep
    """The Section 10.4 step that decided the delivered format."""

    note: str | None = None
    """Step-4 guidance (how to request the image) when ``capability`` is unknown."""

    client: str | None = None
    """The matched client identity (``name version``) when step 3 answered."""

    @property
    def vision(self) -> bool:
        """Whether image blocks may be delivered (never inferred — ADR-006)."""
        return self.capability == CAPABILITY_VISION

    @property
    def text_only(self) -> bool:
        """Whether the session is known incapable of rendering images."""
        return self.capability == CAPABILITY_TEXT_ONLY


def resolve_capability(
    format_preference: str = FORMAT_AUTO,
    *,
    session_capability: str | None = None,
    client_name: str | None = None,
    client_version: str | None = None,
    table: CapabilityTable | None = None,
) -> CapabilityResolution:
    """Apply Section 10.4's resolution order to one attachment read.

    Step 1 short-circuits the *format decision* (a non-``auto`` preference
    is reported as ``explicit_format``); the *capability* is still resolved
    through steps 2→3→4 because Section 9.5's image gate (text-only
    sessions may not silently receive ``image_base64``) needs it either way.
    Step 2 short-circuits step 3; a table miss falls to step 4.
    ``unknown`` always carries :data:`IMAGE_REQUEST_NOTE` so the model knows
    how to ask for the image explicitly.
    """
    capability, step, client = _resolve_session_capability(
        session_capability=session_capability,
        client_name=client_name,
        client_version=client_version,
        table=table,
    )
    note = IMAGE_REQUEST_NOTE if capability == CAPABILITY_UNKNOWN else None
    if format_preference != FORMAT_AUTO:
        return CapabilityResolution(
            format_preference=format_preference,
            capability=capability,
            step=ResolutionStep.EXPLICIT_FORMAT,
            note=None,
            client=client,
        )
    return CapabilityResolution(
        format_preference=FORMAT_AUTO,
        capability=capability,
        step=step,
        note=note,
        client=client,
    )


def _resolve_session_capability(
    *,
    session_capability: str | None,
    client_name: str | None,
    client_version: str | None,
    table: CapabilityTable | None,
) -> tuple[str, ResolutionStep, str | None]:
    """Steps 2→3→4: the capability itself (short-circuiting at each step)."""
    # Step 2: startup configuration. An invalid defensive value behaves as
    # unset (Settings validates the value at startup; never crash a read).
    if isinstance(session_capability, str) and session_capability in CAPABILITIES:
        return session_capability, ResolutionStep.SESSION_CONFIG, None
    # Step 3: the editable client table, when a client identity is known.
    if table is not None and client_name:
        matched = table.lookup(client_name, client_version)
        if matched is not None:
            label = client_name if not client_version else f"{client_name} {client_version}"
            return matched, ResolutionStep.CLIENT_TABLE, label
    # Step 4: the text-safe default (Section 10.9 — unknown is not vision).
    return CAPABILITY_UNKNOWN, ResolutionStep.DEFAULT_TEXT_SAFE, None


def client_identity(context: Any) -> tuple[str | None, str | None]:
    """Best-effort ``(name, version)`` from the MCP handshake context.

    The SDK injects the request ``Context`` into tool handlers
    (``context_kwarg``); its session carries the initialize request params,
    whose ``client_info`` is the client's declared ``Implementation``
    (name/version). Every layer is optional — anonymous/stateless clients,
    unit tests and older handshake shapes all yield ``(None, None)``, which
    the resolver treats as "no step-3 identity" (text-safe default). Never
    raises from a tool call.
    """
    try:
        session = context.session
    except AttributeError:
        return (None, None)
    params = getattr(session, "client_params", None)
    if params is None:
        return (None, None)
    info = getattr(params, "client_info", None)
    if info is None:
        return (None, None)
    name = getattr(info, "name", None)
    version = getattr(info, "version", None)
    return (
        name.strip() if isinstance(name, str) and name.strip() else None,
        version.strip() if isinstance(version, str) and version.strip() else None,
    )
