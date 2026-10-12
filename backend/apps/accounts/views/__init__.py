"""View surface of the accounts app (Section 9.2).

Split per endpoint group (auth / tokens / devices); every view stays a thin
adapter over ``apps.accounts.services`` — business logic never lives here.
"""

from __future__ import annotations

from .auth import LoginView, LogoutView, RefreshView
from .devices import DeviceRegisterView, DeviceRevokeView
from .tokens import AgentTokenIssueView, TokenListView, TokenRevokeView

__all__ = [
    "AgentTokenIssueView",
    "DeviceRegisterView",
    "DeviceRevokeView",
    "LoginView",
    "LogoutView",
    "RefreshView",
    "TokenListView",
    "TokenRevokeView",
]
