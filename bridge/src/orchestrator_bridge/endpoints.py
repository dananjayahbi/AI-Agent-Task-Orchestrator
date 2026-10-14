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
package that has yet to implement it (e.g. claim/release landed with WP-1.6,
checkpoints with WP-1.8, resolution with WP-3.2 — each retired its flag as it
declared). Any other catalog entry
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

__all__ = [
    "BRIDGE_ENDPOINTS",
    "Endpoint",
    "MUTATING_METHODS",
    "PENDING_BACKEND",
    "endpoint",
]

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
    # --- declared in the current document -------------------------------------
    # (WP-3.2's resolution_submit entry retired at convergence: the
    # submission route is in the document and the contract test validates
    # its request sample. WP-1.14's attachment_content entry retired the
    # same way — the content route landed and this catalog lost the flag
    # in the same change, per this file's documented stale-flag rule.)
    Endpoint("attachment_content", "GET", "/api/v1/attachments/{id}/content"),
    Endpoint("checkpoint_create", "POST", "/api/v1/tasks/{id}/checkpoints"),
    Endpoint("resolution_submit", "POST", "/api/v1/tasks/{id}/resolution"),
    Endpoint("attachment_list", "GET", "/api/v1/tasks/{id}/attachments"),
    Endpoint("attachment_get", "GET", "/api/v1/attachments/{id}"),
    Endpoint("session_open", "POST", "/api/v1/agent-sessions"),
    Endpoint("session_end", "POST", "/api/v1/agent-sessions/{id}/end"),
    Endpoint("work_list", "GET", "/api/v1/projects/{pid}/work"),
    Endpoint("claim", "POST", "/api/v1/tasks/{id}/claim"),
    Endpoint("release", "POST", "/api/v1/tasks/{id}/release"),
    Endpoint("audit_verdict", "POST", "/api/v1/tasks/{id}/audit-verdict"),
    Endpoint("task_details", "GET", "/api/v1/tasks/{id}"),
    Endpoint("project_context", "GET", "/api/v1/projects/{pid}"),
    Endpoint("project_policy", "GET", "/api/v1/projects/{pid}/policy"),
    Endpoint("manifest_read", "GET", "/api/v1/projects/{pid}/manifest"),
    Endpoint("task_create_draft", "POST", "/api/v1/projects/{pid}/tasks"),
    # WP-3.7 (MT-3.7-01): the Section 9.2 Merge queue row, in the document —
    # the executor's whole backend surface (MT-3.7-02 consumes it).
    Endpoint("merge_pending", "GET", "/api/v1/merge/pending"),
    Endpoint("merge_start", "POST", "/api/v1/merge/{task}/start"),
    Endpoint("merge_result", "POST", "/api/v1/merge/{task}/result"),
    Endpoint("health_live", "GET", "/health/live"),
)


def endpoint(endpoint_id: str) -> Endpoint:
    """Look up one catalog entry by id — the single source of path truth.

    Handlers and the session layer resolve their paths through this function
    (never by re-typing a path literal), so a backend path change surfaces as
    one catalog edit plus the MT-2.3-05 contract test.
    """
    for entry in BRIDGE_ENDPOINTS:
        if entry.id == endpoint_id:
            return entry
    raise KeyError(f"unknown bridge endpoint id: {endpoint_id!r}")


#: Endpoint id -> the backend work package that will put it in the document.
#: Only these may be absent from ``schemas/openapi.yaml``; absence anywhere
#: else fails the contract test with the endpoint named. (WP-1.8's
#: ``checkpoint_create`` entry retired at convergence: the checkpoint
#: route is in the document and the contract test validates its sample.
#: WP-3.2's ``resolution_submit`` entry retired the same way — the
#: submission route landed and this map lost the flag in the same change,
#: per this file's documented stale-flag rule. WP-1.14's
#: ``attachment_content`` entry retired the same way — the content route
#: landed and this map lost the flag in the same change.)
PENDING_BACKEND: Final[dict[str, str]] = {}
