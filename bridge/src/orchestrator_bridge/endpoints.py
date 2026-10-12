"""The bridge client's REST endpoint catalog (parent plan Section 9.2;
MT-2.3-05).

One declarative table for every v1 endpoint the bridge client calls or is
scheduled to call — the join between the client (``transport``), the Section
9.2 plan table and the generated contract (``schemas/openapi.yaml``, ADR-005).
Paths are the exact OpenAPI spellings (origin-absolute, ``{pid}``/``{id}``
templates as drf-spectacular writes them), so the contract test compares them
1:1 without translation.

Provenance discipline: an endpoint may be absent from the OpenAPI document
**only** while it is listed in :data:`PENDING_BACKEND` with the backend work
package that has yet to implement it (e.g. claim/release land with WP-1.6,
checkpoints with WP-1.8, resolution with WP-3.2). Any other catalog entry
missing from the document fails the contract test by name, and a pending
entry that *appears* in the document is validated immediately — the pending
flag then goes stale and is cleaned up in the same change. The catalog paths
mirror Section 9.2 verbatim, so backend path drift from the plan is what the
test surfaces (never a silent skip).

:attr:`Endpoint.mutating` derives from the HTTP verb (headers.md), keeping
one source of truth for the idempotency-header rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = ["BRIDGE_ENDPOINTS", "Endpoint", "MUTATING_METHODS", "PENDING_BACKEND"]

#: headers.md: all POST/PATCH/PUT/DELETE calls are mutating; reads never are.
MUTATING_METHODS: Final[frozenset[str]] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True, slots=True)
class Endpoint:
    """One bridge-used operation: stable id, verb, and OpenAPI path template."""

    id: str
    method: str
    path: str

    @property
    def mutating(self) -> bool:
        """Whether calls to this endpoint must carry ``Idempotency-Key``."""
        return self.method in MUTATING_METHODS


#: Section 9.2 endpoints the bridge speaks (WP-2.4 onward consumes this table).
BRIDGE_ENDPOINTS: Final[tuple[Endpoint, ...]] = (
    # --- not yet in the generated document: pending, provenance recorded ------
    Endpoint("checkpoint_create", "POST", "/api/v1/tasks/{id}/checkpoints"),
    Endpoint("resolution_submit", "POST", "/api/v1/tasks/{id}/resolution"),
    Endpoint("attachment_list", "GET", "/api/v1/tasks/{id}/attachments"),
    Endpoint("attachment_get", "GET", "/api/v1/attachments/{id}"),
    Endpoint("attachment_content", "GET", "/api/v1/attachments/{id}/content"),
    # --- declared in the current document -------------------------------------
    Endpoint("session_open", "POST", "/api/v1/agent-sessions"),
    Endpoint("session_end", "POST", "/api/v1/agent-sessions/{id}/end"),
    Endpoint("work_list", "GET", "/api/v1/projects/{pid}/work"),
    Endpoint("claim", "POST", "/api/v1/tasks/{id}/claim"),
    Endpoint("release", "POST", "/api/v1/tasks/{id}/release"),
    Endpoint("task_details", "GET", "/api/v1/tasks/{id}"),
    Endpoint("project_context", "GET", "/api/v1/projects/{pid}"),
    Endpoint("manifest_read", "GET", "/api/v1/projects/{pid}/manifest"),
    Endpoint("task_create_draft", "POST", "/api/v1/projects/{pid}/tasks"),
    Endpoint("health_live", "GET", "/health/live"),
)

#: Endpoint id -> the backend work package that will put it in the document.
#: Only these may be absent from ``schemas/openapi.yaml``; absence anywhere
#: else fails the contract test with the endpoint named.
PENDING_BACKEND: Final[dict[str, str]] = {
    "checkpoint_create": "WP-1.8 (MT-1.8-03, checkpoint endpoint)",
    "resolution_submit": "WP-3.2 (backend submission endpoints)",
    "attachment_list": "WP-1.11 (attachment storage and upload API)",
    "attachment_get": "WP-1.11 (attachment storage and upload API)",
    "attachment_content": "WP-1.14 (attachment retrieval API)",
}
