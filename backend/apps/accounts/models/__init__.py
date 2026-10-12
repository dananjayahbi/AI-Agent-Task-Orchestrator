"""Model surface of the ``accounts`` app (Section 9.1).

Re-exports every model so the rest of the codebase imports from
``apps.accounts.models`` — the file-per-entity layout stays an internal
concern (MT-1.2-01, MT-1.2-02, MT-1.2-04 each own their entity file).
"""

from __future__ import annotations

from .devices import Device, Platform
from .tokens import AGENT_ROLE_SCOPES, PROJECT_ID_PATTERN, ApiToken, TokenKind, validate_project_id
from .users import User

__all__ = [
    "AGENT_ROLE_SCOPES",
    "PROJECT_ID_PATTERN",
    "ApiToken",
    "Device",
    "Platform",
    "TokenKind",
    "User",
    "validate_project_id",
]
