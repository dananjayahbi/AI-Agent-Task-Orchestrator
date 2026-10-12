"""Empty tools registry (parent plan Section 10.5; WP-2.1 acceptance: "empty tool set").

Seeded empty by MT-2.1-01 — a data seam only, no registration machinery: WP-2.4
onward defines the tool-handler contract, registers the Section 10.5 tools here and
wires them into ``orchestrator_bridge.server.create_server``. Until then
``create_server`` advertises zero tools (Section 19.1, WP-2.1 acceptance).
"""

from __future__ import annotations

from typing import Final

TOOLS: Final[dict[str, object]] = {}
