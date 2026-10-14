"""URL surface of the audit app — ``/api/v1``-prefixed by the root include.

The Section 9.2 "Audit" and "Review" rows verbatim: ``POST
/tasks/{id}/audit-verdict``, ``GET /tasks/{id}/audit-reports`` (WP-3.3)
and ``POST /tasks/{id}/review`` (WP-3.6) — no trailing slashes (the
convention the other surfaces fixed). Views live in this app
(Section 9.1: ``audit`` owns audit reports, the Policy Engine, review
decisions); the routes are grouped here so the WP's surface stays in one
owned file.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import AuditReportListView, AuditVerdictView, ReviewDecisionView

urlpatterns: list[URLPattern] = [
    path("tasks/<str:id>/audit-verdict", AuditVerdictView.as_view(), name="audit-verdict"),
    path("tasks/<str:id>/audit-reports", AuditReportListView.as_view(), name="audit-reports"),
    path("tasks/<str:id>/review", ReviewDecisionView.as_view(), name="task-review"),
]
