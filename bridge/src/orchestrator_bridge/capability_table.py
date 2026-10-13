"""The editable client capability table (Sections 10.4 step 3, 10.9; MT-2.5-02).

Step 3 of :func:`orchestrator_bridge.capabilities.resolve_capability` looks
the MCP handshake client's name/version up in this table. The table is a
**plain JSON file the operator edits without a bridge release**
(``bridge/capability_table/clients.json``, Appendix A); the bridge reads it
at startup.

Honesty rules (ADR-006; Section 10.9): the shipped table records every
Section 10.9 client at ``unknown`` — "Expected yes", "To verify", "Likely
text-only" and even the plan's stated "Text-only" rows are *not* verified
claims. Only a WP-2.11 conformance run (observe the handshake name, render
an image end-to-end) may flip an entry to ``vision``/``text_only``.

Degrade-don't-crash (MT-2.5-02): a missing, unreadable or malformed file
yields an empty table — every lookup misses and step 4's text-safe default
applies, logged once as a warning. Malformed *entries* are skipped
individually; an unrecognized ``capability`` value becomes ``unknown``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from .capabilities import CAPABILITIES, CAPABILITY_UNKNOWN

__all__ = [
    "CAPABILITY_TABLE_ENV",
    "DEFAULT_CAPABILITY_TABLE_PATH",
    "CapabilityTable",
    "ClientCapability",
    "load_capability_table",
]

logger = logging.getLogger("bridge")

#: Optional operator override of the table path (same-env pattern as
#: ``ORCHESTRATOR_SPOOL_DIR``: one optional file location, no settings churn).
CAPABILITY_TABLE_ENV: Final = "ORCHESTRATOR_BRIDGE_CAPABILITY_TABLE"

#: The shipped file, resolved from the installed package back to the repo's
#: ``bridge/`` root (src layout: …/bridge/src/orchestrator_bridge/…). An
#: installed wheel has no such file — the lookup then degrades to the empty
#: table (text-safe), which is the honest posture for an unshipped table.
DEFAULT_CAPABILITY_TABLE_PATH: Final = (
    Path(__file__).resolve().parents[2] / "capability_table" / "clients.json"
)


def _version_tuple(raw: object) -> tuple[int, ...] | None:
    """Parse a dotted version into comparable ints (non-numeric parts → 0)."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    parts: list[int] = []
    for piece in raw.strip().split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _within(
    version: tuple[int, ...] | None,
    lower: tuple[int, ...] | None,
    upper: tuple[int, ...] | None,
) -> bool:
    """Version-window check; an unparseable/absent caller version misses bounds."""
    if version is None:
        return lower is None and upper is None
    width = max((len(bound) for bound in (lower, upper) if bound is not None), default=0)

    def padded(bound: tuple[int, ...]) -> tuple[int, ...]:
        return bound + (0,) * (width - len(bound))

    current = padded(version)
    if lower is not None and current < padded(lower):
        return False
    if upper is not None and current > padded(upper):
        return False
    return True


@dataclass(frozen=True, slots=True)
class ClientCapability:
    """One table entry: which client names/versions, what capability."""

    client_names: tuple[str, ...]
    capability: str
    min_version: str | None = None
    max_version: str | None = None
    source: str = ""
    notes: str = ""

    def matches(self, name: str, version: str | None) -> bool:
        """Case-insensitive exact name match inside the version window."""
        wanted = name.strip().lower()
        if wanted not in self.client_names:
            return False
        return _within(
            _version_tuple(version),
            _version_tuple(self.min_version),
            _version_tuple(self.max_version),
        )


@dataclass(frozen=True, slots=True)
class CapabilityTable:
    """Parsed entries; ``lookup`` answers with a capability or a miss."""

    entries: tuple[ClientCapability, ...] = ()

    def lookup(self, name: str, version: str | None = None) -> str | None:
        """The first matching entry's capability; ``None`` = no opinion.

        A miss is meaningful: the resolver falls to step 4 (text-safe
        ``unknown``). An entry recorded as ``unknown`` answers explicitly
        ("the table knows this client; nothing is verified yet").
        """
        for entry in self.entries:
            if entry.matches(name, version):
                return entry.capability
        return None


def _text_or_none(value: object) -> str | None:
    """A non-empty string field, or None (table fields are all optional text)."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _parse_entries(data: object) -> list[ClientCapability]:
    """Parse the file's ``clients`` array; skip malformed entries one by one."""
    if not isinstance(data, dict):
        return []
    raw_entries: Iterable[object] = ()
    if isinstance(data.get("clients"), list):
        raw_entries = data["clients"]
    parsed: list[ClientCapability] = []
    for index, raw in enumerate(raw_entries):
        if not isinstance(raw, dict):
            logger.warning("capability table entry %d is not an object; skipped", index)
            continue
        names = raw.get("client_names")
        if not isinstance(names, list) or not all(isinstance(item, str) and item for item in names):
            logger.warning("capability table entry %d has no usable client_names; skipped", index)
            continue
        capability = raw.get("capability")
        if capability not in CAPABILITIES:
            if capability is not None:
                logger.warning(
                    "capability table entry %d has capability %r; recording %s",
                    index,
                    capability,
                    CAPABILITY_UNKNOWN,
                )
            capability = CAPABILITY_UNKNOWN
        parsed.append(
            ClientCapability(
                client_names=tuple(item.strip().lower() for item in names if isinstance(item, str)),
                capability=capability,
                min_version=_text_or_none(raw.get("min_version")),
                max_version=_text_or_none(raw.get("max_version")),
                source=_text_or_none(raw.get("source")) or "",
                notes=_text_or_none(raw.get("notes")) or "",
            )
        )
    return parsed


def _read_table(path: Path) -> CapabilityTable:
    """Read and parse one table file; any failure degrades to the empty table."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        # The normal installed-wheel state (no repo file): no opinion, no crash.
        return CapabilityTable()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning(
            "capability table %s is not valid JSON (%s); treating every client as unknown",
            path,
            exc.msg,
        )
        return CapabilityTable()
    entries = _parse_entries(data)
    if not entries:
        logger.warning("capability table %s parsed to no usable entries; unknown for all", path)
    return CapabilityTable(tuple(entries))


@lru_cache(maxsize=4)
def _load_cached(resolved: str) -> CapabilityTable:
    """Cached per resolved path — an edit needs a process restart (documented)."""
    return _read_table(Path(resolved))


def load_capability_table(path: Path | None = None) -> CapabilityTable:
    """Load the table from *path*, the ``ORCHESTRATOR_BRIDGE_CAPABILITY_TABLE``
    override, or the shipped ``bridge/capability_table/clients.json``.

    Caching is keyed by the resolved path (startup semantics: one load per
    process; editing the file takes effect on the next bridge start). Tests
    pass distinct temporary paths, so they never share a cached entry.
    """
    if path is not None:
        return _load_cached(str(path))
    override = os.environ.get(CAPABILITY_TABLE_ENV)
    if override and override.strip():
        return _load_cached(str(Path(override.strip())))
    return _load_cached(str(DEFAULT_CAPABILITY_TABLE_PATH))
