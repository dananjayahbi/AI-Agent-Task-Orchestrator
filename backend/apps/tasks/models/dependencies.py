"""TASK —N:N— TASK DEPENDENCY (Section 7.1; FR-TSK-07).

One row per directed edge: ``task`` waits on ``depends_on``. The section
spells no columns for the join entity, so the model is deliberately
minimal — the two foreign keys and nothing else — and the write-side
rules (existence, same project, self, cycles) live in
``services/dependencies.py``, where both CRUD paths reach them.

The database backs the two rules it *can* express: an edge is unique
(``task`` waits on a given task at most once) and a task never waits on
itself. Same-project scope and cycle prevention need multi-row context
and are validated in the service (GOAL-2 / ADR-004 spirit; cycle
prevention is a plan reading recorded in the WP changelog).
"""

from __future__ import annotations

from django.db import models

from .task import Task


class TaskDependency(models.Model):
    """One ``task → depends_on`` edge of the Section 7.1 N:N relation."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="dependency_edges",
        help_text="The waiting task (the dependent).",
    )
    depends_on = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="dependent_edges",
        help_text="The completed-first task (the blocking dependency).",
    )

    class Meta:
        """Uniqueness and no-self-edge at the DB level (Section 7.4 spirit)."""

        constraints = [
            models.UniqueConstraint(
                fields=["task", "depends_on"],
                name="task_dependency_unique_edge",
            ),
            models.CheckConstraint(
                condition=~models.Q(task=models.F("depends_on")),
                name="task_dependency_no_self_edge",
            ),
        ]

    def __str__(self) -> str:
        """``{task} depends_on {depends_on}`` — the edge, read aloud."""
        return f"{self.task_id} depends_on {self.depends_on_id}"
