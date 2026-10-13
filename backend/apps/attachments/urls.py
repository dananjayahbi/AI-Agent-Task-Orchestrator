"""URL surface of the attachments app — ``/api/v1``-prefixed by the root include.

Paths mirror the Section 9.2 Attachments row verbatim: ``POST/GET
/tasks/{id}/attachments``, ``GET/DELETE /attachments/{id}`` and — since
WP-1.14 landed it — ``GET /attachments/{id}/content?format=&page=``
(the one page-numbered route; pagination.md's documented content
exception).
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import AttachmentDetailView, AttachmentListCreateView
from .views_content import AttachmentContentView

urlpatterns: list[URLPattern] = [
    path(
        "tasks/<str:id>/attachments",
        AttachmentListCreateView.as_view(),
        name="task-attachments",
    ),
    path("attachments/<str:id>", AttachmentDetailView.as_view(), name="attachment-detail"),
    path(
        "attachments/<str:id>/content",
        AttachmentContentView.as_view(),
        name="attachment-content",
    ),
]
