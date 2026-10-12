"""Upward manifest discovery: cwd → Git root (parent plan Section 10.3 step 1; MT-2.2-01).

The walk starts at the current working directory and moves to the parent
directory until it finds ``orchestrator.json`` or passes the Git repository root
(Section 10.3 verbatim; FR-MCP-02 per-repo binding). Rules fixed here
(MT-2.2-01 risk notes):

* **first-found wins, ceiling = Git root** — the nearest manifest from the cwd
  upward is the bound one (a nested manifest, if present, *is* the nearest);
  a decoy above the repository is never consulted.
* **``.git`` defines the ceiling** — directory (normal repo) or file (worktree /
  submodule pointer): its location *is* the root boundary; that directory is
  checked for a manifest and then the walk stops (a manifest at the Git root is
  found; the pointer file itself is never walked past).
* **no Git root** (exported tree, tarball): the walk caps at the filesystem root
  and fails with the same not-found message, worded for that case (recorded in
  the WP changelog).
* **not found never falls back** — the bridge refuses to start unbound and
  points at ``orchestrator init`` (Section 10.11); there is no silent unbound
  session (FR-MCP-02).

A test-only override (``settings.manifest_path`` from MT-2.1-02,
``ORCHESTRATOR_BRIDGE_MANIFEST_PATH``) bypasses the walk for tests and non-repo
invocations. Production discovery consults it only when explicitly configured —
the default flow is always the upward walk.

Discovery locates and structurally parses the file: JSON/UTF-8 syntax problems
surface here as :class:`ManifestParseError`. Schema and version validation is
the separate MT-2.2-02 seam (:mod:`manifest_validation`) — this module never
looks inside the document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import INIT_COMMAND, ManifestNotFoundError, ManifestParseError

__all__ = [
    "MANIFEST_FILENAME",
    "DiscoveredManifest",
    "discover_manifest",
]

#: The one manifest filename per repo root (plan glossary; Section 10.3).
MANIFEST_FILENAME = "orchestrator.json"


@dataclass(frozen=True, slots=True)
class DiscoveredManifest:
    """Where the manifest is and what it parsed to — path plus raw JSON value."""

    path: Path
    document: object


def _not_found_error(cwd: Path, *, reached_git_root: bool) -> ManifestNotFoundError:
    """The one fail-fast message, worded for the ceiling that stopped the walk."""
    scope = (
        "the repository root"
        if reached_git_root
        else "the filesystem root (no Git repository found)"
    )
    return ManifestNotFoundError(
        f"no {MANIFEST_FILENAME} found from {cwd} upward to {scope}; "
        f"run '{INIT_COMMAND}' in the repository to create one"
    )


def _read_document(path: Path) -> object:
    """Read and structurally parse one manifest file (semantics belong to MT-2.2-02)."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ManifestParseError(f"manifest {path} is not valid UTF-8 text") from None
    except OSError as exc:
        raise ManifestParseError(f"cannot read manifest {path}: {exc.strerror or exc}") from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestParseError(f"manifest {path} is not valid JSON: {exc}") from None


def _walk_up(start: Path) -> tuple[Path | None, bool]:
    """Walk *start* upward: ``(manifest path | None, stopped at a Git root)``.

    The directory is checked for a manifest *before* the ``.git`` ceiling, so a
    manifest sitting at the Git root is found and only then does the walk stop.
    """
    current = start
    while True:
        candidate = current / MANIFEST_FILENAME
        if candidate.is_file():
            return candidate, True
        if (current / ".git").exists():
            return None, True
        parent = current.parent
        if parent == current:
            return None, False  # filesystem root reached with no .git anywhere
        current = parent


def discover_manifest(
    cwd: Path | None = None,
    *,
    override: Path | None = None,
) -> DiscoveredManifest:
    """Locate and parse the manifest for *cwd* (default: the process working dir).

    *override* (from ``settings.manifest_path``) bypasses the walk entirely —
    tests and non-repo invocations only (module docstring). Raises
    :class:`ManifestNotFoundError` when nothing is found and
    :class:`ManifestParseError` when the file cannot be read/parsed; neither ever
    falls back to an unbound run.
    """
    start = (Path.cwd() if cwd is None else cwd).resolve()
    if override is not None:
        path = override if override.is_absolute() else start / override
        path = path.resolve()
        if not path.is_file():
            raise ManifestNotFoundError(
                f"manifest override {path} does not exist or is not a file; "
                f"unset it or point it at an existing {MANIFEST_FILENAME}"
            )
        return DiscoveredManifest(path=path, document=_read_document(path))

    found, reached_git_root = _walk_up(start)
    if found is None:
        raise _not_found_error(start, reached_git_root=reached_git_root)
    return DiscoveredManifest(path=found.resolve(), document=_read_document(found))
