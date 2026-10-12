"""Manifest discovery, schema validation and session binding (Section 10.3; WP-2.2).

:func:`bind_startup` composes the first three steps of the Section 10.3 startup
sequence, strictly in order —

1. discover (:mod:`manifest_discovery`: cwd → Git root),
2. validate (:mod:`manifest_validation`: published schema + version check),
3. load the token (:mod:`credentials`: environment or user-level config,
   never the manifest),

— so an invalid manifest aborts before any credential is even consulted
(FR-SEC-01 hygiene) and a missing token aborts before any session call. Steps 4–5
(session open, project-context cache — MT-2.2-04) and the project-mismatch abort
(MT-2.2-05) are the downstream consumers of :class:`StartupBinding` and land
when ``POST /agent-sessions`` exists; the token is deliberately *not* part of
the binding result (``Settings`` stays the single holder and redaction
boundary).

The binding derives nothing the backend owns (Section 19.3): the returned
manifest is the validated document as-is — no policy, no token decoding, no
project comparison. The manifest holds no secrets and is not a configuration
source (FR-SEC-04); ``orchestrator_api`` precedence versus ``api_base_url``,
deferred here to WP-2.3, is resolved there — the manifest wins
(``transport.ApiClient.for_binding``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .credentials import require_agent_token
from .manifest_discovery import discover_manifest
from .manifest_validation import validate_manifest

__all__ = ["StartupBinding", "bind_startup"]


@dataclass(frozen=True, slots=True)
class StartupBinding:
    """The validated manifest bound to this process (the MT-2.2-04/05 seam)."""

    manifest_path: Path
    manifest: Mapping[str, Any]

    @property
    def project_id(self) -> str:
        """The bound project id — schema-guaranteed ``^PID[0-9]{5}$`` string."""
        return str(self.manifest["project_id"])


def bind_startup(settings: Settings, *, cwd: Path | None = None) -> StartupBinding:
    """Run Section 10.3 steps 1–3 in order; raise a ``BindingError`` on failure.

    *cwd* defaults to the process working directory (tests inject). Discovery
    honors the test-only ``settings.manifest_path`` override; validation runs
    before the token gate so no credential is read for an invalid manifest.
    """
    discovered = discover_manifest(cwd, override=settings.manifest_path)
    validated = validate_manifest(discovered.document, source=discovered.path)
    require_agent_token(settings)  # step 3 — the value stays in settings
    return StartupBinding(manifest_path=discovered.path, manifest=validated)
