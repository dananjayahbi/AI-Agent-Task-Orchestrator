"""URL surface of the tasks app — ``/api/v1``-prefixed by the root router.

Paths mirror the Section 9.2 Tasks row verbatim (``/projects/{pid}/tasks``,
``/tasks/{id}``) — no trailing slashes (the convention the accounts and
projects surfaces fixed). ``POST /tasks/{id}/transition`` (WP-1.5),
``GET /projects/{pid}/work`` (WP-1.6) and the remaining Section 9.2 task
sub-resources join from their owning work packages; the deferred-route
drift guards in ``tests/test_authorization_matrix.py`` fail the moment
one lands without its authorization case.
"""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import TaskDetailView, TaskListCreateView

urlpatterns: list[URLPattern] = [
    path(
        "projects/<str:pid>/tasks",
        TaskListCreateView.as_view(),
        name="task-list-create",
    ),
    path("tasks/<str:id>", TaskDetailView.as_view(), name="task-detail"),
]
