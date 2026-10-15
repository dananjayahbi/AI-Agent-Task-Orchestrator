"""URL surface of the notifications app — ``/api/v1``-prefixed by the root.

Section 9.2 lists no notifications row (the preferences endpoint is
MT-5.4-05's contract addition, schema-diffed with the other WPs); the path
follows the resource style of the table: ``/notifications/preferences``.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import NotificationPreferencesView

urlpatterns: list[URLPattern] = [
    path(
        "notifications/preferences",
        NotificationPreferencesView.as_view(),
        name="notification-preferences",
    ),
]
