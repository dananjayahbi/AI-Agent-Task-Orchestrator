"""MT-1.6-03 — lease extension with the hard total-age cap (Section 8.6; FR-LEA-03).

Run with ``pytest backend/tests -k lease_extension -q``. The formula
lives here; its production caller (the checkpoint endpoint) is WP-1.8's
MT-1.8-03. Clock note (MT-1.6-03 risk): the service compares against
``django.utils.timezone.now()`` — one documented source.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.leases.exceptions import LeaseExpired, LeaseNotOwned
from apps.leases.extension import LeaseExtension, extend_lease
from apps.projects.models import Project
from apps.tasks.models import Task

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _claimed(**policy_fields: Any) -> tuple[Project, Task]:
    """One project with tuned policy and one task claimed by sess_owner."""
    project = active_policy_project(**policy_fields)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_owner")
    task.refresh_from_db()
    return project, task


def _extend(
    task: Task, *, session_id: str = "sess_owner", generation: int | None = None
) -> LeaseExtension:
    """Extend *task* as its holder (or a supplied fencing pair)."""
    return extend_lease(
        task_id=task.pk,
        session_id=session_id,
        lease_generation=task.lease_generation if generation is None else generation,
        caller_project_id=task.project_id,
    )


def test_fresh_extension_uses_the_formula() -> None:
    """min(now + duration, acquired + cap) — Section 8.6 verbatim."""
    project, task = _claimed()
    before = timezone.now()

    result = _extend(task)

    after = timezone.now()
    assert result.task_id == task.pk
    assert result.capped is False
    assert result.lease_expires_at is not None
    low = before + timedelta(minutes=project.agent_policy.lease_duration_minutes)
    high = after + timedelta(minutes=project.agent_policy.lease_duration_minutes)
    assert low <= result.lease_expires_at <= high
    task.refresh_from_db()
    assert task.lease_expires_at == result.lease_expires_at
    assert task.version == 3, "the extension is a row change (Section 7.2 bump)"


def test_extension_clamps_exactly_to_the_hard_cap() -> None:
    """Near the cap the value stops at acquired + lease_max_total_minutes."""
    project, task = _claimed()
    # Backdate the lease start so now + 45 would overshoot the 240 cap.
    acquired = timezone.now() - timedelta(minutes=200)
    Task.objects.filter(pk=task.pk).update(lease_acquired_at=acquired)
    task.refresh_from_db()

    result = _extend(task)

    assert result.capped is True
    assert result.lease_expires_at == acquired + timedelta(
        minutes=project.agent_policy.lease_max_total_minutes
    )


def test_repeated_extensions_never_exceed_the_cap() -> None:
    """No sequence of extensions moves past acquired + cap (WP-1.8 check)."""
    project, task = _claimed()
    acquired = timezone.now() - timedelta(minutes=210)
    Task.objects.filter(pk=task.pk).update(lease_acquired_at=acquired)
    cap = acquired + timedelta(minutes=project.agent_policy.lease_max_total_minutes)

    expires = None
    for _ in range(6):
        task.refresh_from_db()
        result = _extend(task)
        assert result.lease_expires_at <= cap
        expires = result.lease_expires_at

    assert expires == cap, "the last clamp lands exactly on the cap"


def test_successive_extensions_are_non_decreasing() -> None:
    """The formula only grows an unexpired lease (monotone under the cap)."""
    project, task = _claimed()
    seen: list[Any] = []
    for _ in range(3):
        task.refresh_from_db()
        seen.append(_extend(task).lease_expires_at)
    assert seen == sorted(seen)
    assert project.agent_policy.lease_duration_minutes == 45


def test_custom_policy_values_are_honored() -> None:
    """Durations come from the policy row — 10/60 here, not 45/240."""
    project, task = _claimed(lease_duration_minutes=10, lease_max_total_minutes=60)
    acquired = timezone.now() - timedelta(minutes=55)
    Task.objects.filter(pk=task.pk).update(lease_acquired_at=acquired)
    task.refresh_from_db()

    result = _extend(task)

    assert result.capped is True
    assert result.lease_expires_at == acquired + timedelta(minutes=60)


def test_expired_lease_cannot_be_extended() -> None:
    """Section 8.6 "Expire": no resurrection — LEASE_EXPIRED (409)."""
    _, task = _claimed()
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    task.refresh_from_db()
    version_before = task.version

    with pytest.raises(LeaseExpired) as caught:
        _extend(task)

    assert caught.value.status_code == 409
    task.refresh_from_db()
    assert task.version == version_before, "a refusal writes nothing"


def test_stale_generation_cannot_be_extended() -> None:
    """ADR-012 fencing: a previous generation answers LEASE_EXPIRED."""
    _, task = _claimed()
    with pytest.raises(LeaseExpired):
        _extend(task, generation=task.lease_generation - 1)


def test_foreign_session_cannot_be_extended() -> None:
    """Ownership: only the holding session extends — LEASE_NOT_OWNED (403)."""
    _, task = _claimed()
    with pytest.raises(LeaseNotOwned) as caught:
        _extend(task, session_id="sess_intruder")
    assert caught.value.status_code == 403
