"""URL surface of the merge app — ``/api/v1``-prefixed by the root include.

The Section 9.2 *Merge queue* row verbatim: ``GET /merge/pending``,
``POST /merge/{task}/start``, ``POST /merge/{task}/result`` — no
trailing slashes (the convention the other surfaces fixed). Views live
in this app (Section 9.1: ``merge`` owns the queue API the Merge
Executor consumes); the routes are grouped here so the WP's surface
stays in one owned file.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import MergePendingView, MergeResultView, MergeStartView

urlpatterns: list[URLPattern] = [
    path("merge/pending", MergePendingView.as_view(), name="merge-pending"),
    path("merge/<str:task>/start", MergeStartView.as_view(), name="merge-start"),
    path("merge/<str:task>/result", MergeResultView.as_view(), name="merge-result"),
]
