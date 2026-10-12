"""Per-connection and per-event authorization (Sections 9.6, 12.1, 12.2).

Two halves of Section 9.6's rule ("Authorization is evaluated per
connection and per event — Owner sees all; agents never subscribe"):

* **Per connection** — WP-1.2's ``CanReadEvents`` (the Section 12.2 "Read
  events" row: Owner yes, Device yes, every agent role **no**) guards both
  endpoints before any stream exists; this module adds the *scope* read
  that is fixed at connect time from the credential that authenticated.
* **Per event** — :meth:`StreamScope.allows` is the single policy
  predicate every delivery path applies *before serialization to the
  socket*: live fan-out (``StreamConnection.accepts``), resume replay
  (``resume.missed_envelopes`` re-checks it), and history (the queryset
  narrows to the scope). One implementation, three call sites — the
  MT-1.10-05 risk note ("a check applied only in the fan-out module would
  leave replay and history open") is answered structurally.

Scope reading (the "Owner sees all" cell): only **agent** tokens are
project-bound (Section 7.2 / ADR-004), and an agent token can never pass
``CanReadEvents`` — so today's scope is always owner-wide. The scope is
still taken from the credential (``ApiToken.project_id``) so that any
future scoped device credential narrows in exactly this one place, and the
MT's cross-project tests pin the behavior through a directly-built scoped
token row. The client's ``project``/``task`` query filters are the
*visibility narrowing* half of Section 12.1's cross-project-leakage
mitigation, layered on top of the scope.

Revocation of a device token mid-stream is WP-5.3's acceptance ("rejected
on stream reconnect") — this module does not implement it (MT-1.10-05
out of scope).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from apps.accounts.models import ApiToken


@dataclass(frozen=True)
class StreamScope:
    """The connection's visible project set, fixed at connect time.

    ``project_id`` ``None`` means owner-wide visibility (the Section 12.2
    Owner cell and, today, every Device — devices belong to the owner's
    account, MT-1.10-05 risk note). A non-``None`` value confines every
    delivery to that project.
    """

    project_id: str | None = None

    def allows(self, envelope: Mapping[str, Any]) -> bool:
        """Per-event check: the envelope's project falls inside the scope."""
        return self.project_id is None or envelope.get("project_id") == self.project_id

    def narrowed_queryset(self, queryset: Any) -> Any:
        """The same check for row-based paths (history): filter the queryset."""
        if self.project_id is not None:
            return queryset.filter(project_id=self.project_id)
        return queryset


def scope_for_request(request: Any) -> StreamScope:
    """Resolve the visible scope from the authenticated credential.

    Reads ``request.auth`` (the ``ApiToken`` row DRF's authentication
    resolved — never client input; ADR-004: the token, not the request,
    defines scope). Unauthenticated callers never reach this: the
    permission classes answer ``AUTH_REQUIRED`` first.
    """
    token = request.auth
    if isinstance(token, ApiToken):
        return StreamScope(project_id=token.project_id)
    return StreamScope()


__all__ = ["StreamScope", "scope_for_request"]
