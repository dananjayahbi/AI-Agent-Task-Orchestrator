"""URL surface of the attachments app — ``/api/v1``-prefixed by the root include.

Paths mirror the Section 9.2 Attachments row verbatim: ``POST/GET
/tasks/{id}/attachments`` and ``GET/DELETE /attachments/{id}``. The
``content`` retrieval route (``GET /attachments/{id}/content?format=
&page=``) is **WP-1.14** — it stays in the deferred-route drift guards
until that WP lands it (MT-1.11-04 out-of-scope note).
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import AttachmentDetailView, AttachmentListCreateView

urlpatterns: list[URLPattern] = [
    path(
        "tasks/<str:id>/attachments",
        AttachmentListCreateView.as_view(),
        name="task-attachments",
    ),
    path("attachments/<str:id>", AttachmentDetailView.as_view(), name="attachment-detail"),
]
