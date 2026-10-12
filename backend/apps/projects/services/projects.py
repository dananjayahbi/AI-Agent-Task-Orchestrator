"""Business writes and lookups for the project registry (Section 9.1).

Views stay thin: creation composes the Section 7.1 pair (PID from the
MT-1.3-01 sequence + a default ProjectPolicy) inside one transaction, and
every project-addressed view resolves its ``{pid}`` through
``get_project_or_404`` so boundary validation and the unknown-id answer are
decided once.
"""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import NotFound

from ..models import Project, ProjectPolicy
from .pids import allocate_project_id, ensure_valid_pid


def create_project(
    *,
    name: str,
    repo_path: str,
    default_branch: str,
    system_prompt_rules: str = "",
) -> Project:
    """Create the Section 7.1 pair atomically: default policy + new project.

    The PID is server-assigned (FR-PRJ-01 — no client id reaches this
    function; the strict request serializers already reject one) and the
    ProjectPolicy row carries exactly the Section 7.2 defaults (MT-1.3-02;
    editing it later is ``PATCH /projects/{pid}/policy`` — MT-1.3-04).
    Either the pair exists after this call or neither row does.

    Section 9.6 event hook (MT-1.3-03 scope note): ``project.created`` is
    emitted here once WP-1.9's after-commit event helper exists — until
    then this comment is the recorded emission point, not an event.
    """
    with transaction.atomic():
        pid = allocate_project_id()  # raises PidSequenceExhausted → rollback
        policy = ProjectPolicy.objects.create()
        project = Project.objects.create(
            id=pid,
            name=name,
            repo_path=repo_path,
            default_branch=default_branch,
            system_prompt_rules=system_prompt_rules,
            agent_policy=policy,
        )
    return project


def get_project_or_404(pid: str) -> Project:
    """Resolve ``{pid}`` at the API boundary, policy pre-joined.

    Malformed ids raise the DRF ``ValidationError`` → ``VALIDATION_ERROR``
    (Section 7.3: every boundary validates). Unknown ids raise DRF
    ``NotFound``, which ``apps/core/exceptions.py`` deliberately maps to
    ``VALIDATION_ERROR``/400 because **the catalog has no
    ``PROJECT_NOT_FOUND``** (Section 9.2 closed list; MT-1.3-03 risk note —
    the asymmetry with ``TASK_NOT_FOUND`` is recorded in the changelog
    rather than inventing a code). Both answers stay catalog-clean; the
    ``details`` distinguish "malformed" from "unknown".
    """
    ensure_valid_pid(pid)
    project = Project.objects.filter(pk=pid).select_related("agent_policy").first()
    if project is None:
        raise NotFound(f"Project {pid} does not exist.")
    return project
