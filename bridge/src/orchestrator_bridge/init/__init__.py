"""``orchestrator init`` — one-time repository onboarding (FR-MCP-08; Section 10.11; WP-2.12).

Four duties in FR-MCP-08 order, one command, no manual editing (WP-2.12's
"usable in under 2 minutes" acceptance):

1. **Manifest write** (``manifest_write``; MT-2.12-01) — resolve the Git root,
   verify the project against the backend (Section 19.3: ids come from the
   API, never client-derived), write a schema-valid ``orchestrator.json``.
2. **Token storage** (``token_store``; MT-2.12-02) — take the agent token from
   a hidden prompt or the environment and merge it into the user-level TOML
   outside the repository (FR-SEC-04; never argv, never echoed).
3. **Connectivity self-test** (``selftest``; MT-2.12-03) — manifest valid,
   token resolvable (source named, value never shown), then a real
   session-open probe via the MT-2.2-04 client, closed afterwards; per-check
   verdicts, non-zero exit on any failure.
4. **Client snippets** (``snippets``; MT-2.12-04) — after a *passing*
   self-test only (safe ordering), print per-client Section 10.9 MCP
   registration blocks: secret-free, machine-generated terminal output.

``cli`` wires the duties into the ``orchestrator init`` command (declared in
``pyproject.toml``) and the ``python -m orchestrator_bridge.init`` module
entry; ``init --self-test`` re-runs duty 3 standalone for re-verification.
"""

from __future__ import annotations
