"""URL surface of the accounts app — ``/api/v1``-prefixed by the root router.

Paths mirror the Section 9.2 table verbatim (``/auth/login``, ``/auth/logout``,
``/auth/refresh``; ``/tokens/agent``, ``/tokens``, ``/tokens/{id}``;
``/devices``, ``/devices/{id}``).
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import (
    AgentTokenIssueView,
    DeviceRegisterView,
    DeviceRevokeView,
    LoginView,
    LogoutView,
    RefreshView,
    TokenListView,
    TokenRevokeView,
)

urlpatterns: list[URLPattern] = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("tokens/agent", AgentTokenIssueView.as_view(), name="agent-token-issue"),
    path("tokens", TokenListView.as_view(), name="token-list"),
    path("tokens/<int:pk>", TokenRevokeView.as_view(), name="token-revoke"),
    path("devices", DeviceRegisterView.as_view(), name="device-register"),
    path("devices/<int:pk>", DeviceRevokeView.as_view(), name="device-revoke"),
]
