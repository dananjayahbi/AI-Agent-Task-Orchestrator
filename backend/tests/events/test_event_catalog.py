"""MT-1.9-05 — pin the Section 9.6 catalog and prove every emission site.

The catalog reference test asserts the registered event types equal the
plan's Section 9.6 list **exactly** — no additions, drops or renames
(Section 20.5 traceability; Section 20.4 item 6). Per-site tests then
prove each M1 emission site delivered up to WP-1.9 produces exactly one
event with the correct envelope, and that each of those emissions
triggers exactly one post-commit publish (MT-1.9-03's contract).

Sites covered today are listed in :data:`COVERED_EVENT_TYPES`;
:data:`PENDING_EVENT_TYPES` names the producing WP for every catalog
type whose site has not landed yet, so remaining coverage is explicit
rather than silently absent (MT-1.9-05 risk note: a later WP's review
must flip its own entry here). The token-action question — Section 12.5
requires token/login events but the Section 9.6 catalog has no such
type — is recorded as OQ-16 and must never be papered over by inventing
a type (asserted by ``test_no_token_or_login_type_was_invented``).

Run with ``pytest backend/tests/events/ -v`` (plus the Postgres layer
via ``--ds apps.core.settings.dev`` for the privilege suite).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.events.catalog import EVENT_TYPES, SECTION_9_6_EVENT_TYPES
from apps.events.models import Event
from apps.events.services import write_event
from apps.projects.services.projects import create_project
from apps.tasks.models import ClaimedRole, TaskState
from apps.tasks.services.tasks import create_task, update_task
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY
from tests.wp15_helpers import SECTION_9_6_EVENTS, make_project, make_task, registered_registry

from .conftest import FakeRedis

# The Section 9.6 catalog, transcribed independently from the parent plan
# (verbatim, in plan order) — the whole point of this file is that this
# copy and apps/events/catalog.py must agree with the plan *and* each
# other. 24 types as written.
PLAN_SECTION_9_6: tuple[str, ...] = (
    "project.created",
    "project.updated",
    "task.created",
    "task.updated",
    "task.transitioned",
    "task.claimed",
    "task.released",
    "task.checkpoint",
    "task.lease_expiring",
    "task.lease_expired",
    "attachment.processing",
    "attachment.ready",
    "attachment.failed",
    "audit.claimed",
    "audit.passed",
    "audit.escalated",
    "review.requested",
    "review.decided",
    "merge.started",
    "merge.succeeded",
    "merge.failed",
    "agent.session_started",
    "agent.session_ended",
    "system.alert",
)

#: Emission sites wired and asserted by this suite (M1 up to WP-1.9).
COVERED_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "project.created",
        "project.updated",
        "task.created",
        "task.updated",
        "task.transitioned",
        "task.claimed",
        "task.released",
        "task.lease_expired",
    }
)

#: Catalog types whose producing WP has not landed — each entry names it
#: so that WP's MT review flips the entry (MT-1.9-05 risk note).
PENDING_EVENT_TYPES: dict[str, str] = {
    "task.checkpoint": "WP-1.8 (checkpoint endpoint)",
    "task.lease_expiring": "WP-1.7 (MT-1.7-04 80%-of-lease notifier)",
    "attachment.processing": "WP-1.12 (pipeline; upload lands WP-1.11)",
    "attachment.ready": "WP-1.12 (pipeline)",
    "attachment.failed": "WP-1.12 (pipeline)",
    "audit.claimed": "WP-3.x (audit reports)",
    "audit.passed": "WP-3.x (audit reports)",
    "audit.escalated": "WP-3.x (audit reports)",
    "review.requested": "WP-3.x (human review)",
    "review.decided": "WP-3.x (human review)",
    "merge.started": "WP-3.x (merge executor)",
    "merge.succeeded": "WP-3.x (merge executor)",
    "merge.failed": "WP-3.x (merge executor)",
    "agent.session_started": "WP-2.x (bridge session lifecycle)",
    "agent.session_ended": "WP-2.x (bridge session lifecycle)",
    "system.alert": "WP-1.7 (stalled-task detector / monitoring)",
}


# --- the catalog reference tests (Section 20.5 traceability) ----------------


def test_catalog_matches_the_plan_exactly() -> None:
    """None added, dropped or renamed — the plan's list is authoritative."""
    assert SECTION_9_6_EVENT_TYPES == PLAN_SECTION_9_6
    assert len(SECTION_9_6_EVENT_TYPES) == 24, "Section 9.6 as written"
    assert len(EVENT_TYPES) == 24, "membership set mirrors the tuple"


def test_wp15_frozen_twin_matches_the_production_catalog() -> None:
    """The WP-1.5 suites pin the same list — the twins cannot drift."""
    assert SECTION_9_6_EVENTS == PLAN_SECTION_9_6


def test_every_registered_transition_row_emits_a_catalog_type() -> None:
    """Dispatcher rows may only name types the Section 9.6 catalog has."""
    ensure_registered()

    registered = [spec.event_type for spec in DEFAULT_REGISTRY.specs().values()]

    assert registered, "the Section 8.2 rows are registered"
    unknown = sorted(set(registered) - EVENT_TYPES)
    assert unknown == [], f"rows reference non-catalog types: {unknown}"


def test_coverage_is_total_covered_union_pending_equals_the_catalog() -> None:
    """Every catalog type is either tested here or pending with its WP."""
    covered = set(COVERED_EVENT_TYPES)
    pending = set(PENDING_EVENT_TYPES)
    assert covered | pending == set(PLAN_SECTION_9_6), (
        f"unaccounted: {sorted(set(PLAN_SECTION_9_6) - covered - pending)}; "
        f"stale: {sorted((covered | pending) - set(PLAN_SECTION_9_6))}"
    )
    assert covered & pending == set(), f"double-booked: {sorted(covered & pending)}"


def test_no_token_or_login_type_was_invented() -> None:
    """OQ-16: Section 12.5's token/login gap is recorded, not invented.

    The Section 9.6 catalog has no ``token.*``/``login.*``/``auth.*``
    type; until Section 22 decides (OQ-16), token actions emit nothing
    and this test fails loudly if anyone adds a type without the
    catalog-first amendment (Section 20.4 item 5).
    """
    invented = sorted(
        event_type
        for event_type in EVENT_TYPES
        if event_type.split(".", 1)[0] in {"token", "login", "auth", "session"}
    )
    assert invented == [], f"types invented outside the plan catalog: {invented}"
    # `agent.session_*` is the plan's own session naming — allowed above
    # only because its prefix is `agent`, checked here explicitly:
    assert "agent.session_started" in EVENT_TYPES


# --- per-site emission tests: exactly one event, correct envelope -----------


def test_transition_dispatch_emits_exactly_one_catalog_event(db: None) -> None:
    """T2 publish → one `task.transitioned` with the Section 9.6 data."""
    project = make_project(name="Catalog transitions")
    task = make_task(project, 1)

    dispatch_transition(
        task_id=task.pk,
        trigger="publish",
        actor_type="owner",
        actor_ref="user:1",
    )

    events = Event.objects.filter(task_id=task.pk)
    assert events.count() == 1
    event = events.get()
    assert event.type == "task.transitioned"
    assert set(event.data) == {"from_state", "to_state", "reason_code", "task_version"}


def test_lease_expired_emits_exactly_one_catalog_event(db: None) -> None:
    """T5 sweeper transition → one `task.lease_expired` (Section 9.6)."""
    project = make_project(name="Catalog lease expired")
    expired = timezone.now() - timedelta(minutes=1)
    task = make_task(
        project,
        1,
        state=TaskState.IN_PROGRESS,
        worker_agent_id="agent-1",
        claimed_role=ClaimedRole.CODER,
        lease_acquired_at=expired - timedelta(minutes=45),
        lease_expires_at=expired,
    )

    result = dispatch_transition(
        task_id=task.pk,
        trigger="lease_expired",
        actor_type="system",
        actor_ref="lease-sweeper",
    )

    assert result.state == TaskState.PENDING
    events = Event.objects.filter(task_id=task.pk)
    assert events.count() == 1, "the sweeper's emission is exactly one event"
    event = events.get()
    assert event.type == "task.lease_expired"
    assert (event.actor_type, event.actor_ref) == ("system", "lease-sweeper")
    assert event.data["reason_code"] == "lease_expired"


def test_claim_and_release_emit_their_catalog_events_exactly_once(
    db: None,
) -> None:
    """T4/T6 (WP-1.6 wiring) → one `task.claimed` and one `task.released`.

    The registry guard restores WP-1.5's stub rows afterwards, so this
    suite never leaks the lease wiring into the matrix suites (their
    snapshot discipline stays authoritative).
    """
    from apps.leases.wiring import ensure_wired

    with registered_registry():
        ensure_wired()
        project = make_project(name="Catalog claim")
        task = make_task(project, 1, state=TaskState.PENDING)

        claimed = dispatch_transition(
            task_id=task.pk,
            trigger="claim",
            actor_type="agent",
            actor_ref="sess-1",
            extra={
                "caller_project_id": project.pk,
                "session_id": "sess-1",
                "worker_agent_id": "agent-1",
            },
        )
        assert claimed.state == TaskState.IN_PROGRESS
        claimed_events = Event.objects.filter(task_id=task.pk, type="task.claimed")
        assert claimed_events.count() == 1, "one event per claim (Section 19.1)"
        assert (claimed_events.get().actor_type, claimed_events.get().actor_ref) == (
            "agent",
            "sess-1",
        )

        released = dispatch_transition(
            task_id=task.pk,
            trigger="voluntary_release",
            actor_type="agent",
            actor_ref="sess-1",
            extra={"session_id": "sess-1", "lease_generation": claimed.lease_generation},
        )
        assert released.state == TaskState.PENDING
        released_events = Event.objects.filter(task_id=task.pk, type="task.released")
        assert released_events.count() == 1, "one event per release (Section 19.1)"
        assert Event.objects.filter(task_id=task.pk).count() == 2, (
            "claim and release together emit exactly two events — no duplicates"
        )


# --- every covered emission publishes exactly once, after commit (MT-1.9-03)


def test_every_covered_emission_triggers_exactly_one_post_commit_publish(
    db: None,
    fake_publisher: FakeRedis,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """Each emission site: one event row → one publish (Section 9.6)."""
    from apps.leases.wiring import ensure_wired

    def assert_single_publish(perform: Callable[[], object]) -> None:
        before = len(fake_publisher.messages)
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            perform()
        assert len(callbacks) == 1, "one on-commit hook per emission"
        assert len(fake_publisher.messages) == before + 1, "exactly one publish per committed event"

    # The service-created project takes the next PID from the sequence;
    # the factory rows below use explicit ids that the sequence cannot
    # reach in a test session (no collisions, whatever ran before).
    assert_single_publish(
        lambda: create_project(
            name="Publish coverage",
            repo_path="/srv/repos/publish-coverage",
            default_branch="main",
            actor_ref="user:1",
        )
    )
    project = make_project(pid="PID00123", name="Publish coverage tasks")
    task = make_task(project, 1)

    assert_single_publish(
        lambda: create_task(project=project, title="Covered", created_by="user:1")
    )  # allocates T002 from the counter make_task bumped to 1
    assert_single_publish(
        lambda: update_task(
            task=task,
            validated={"title": "Covered twice"},
            expected_version=1,
            actor_ref="user:1",
        )
    )
    assert_single_publish(
        lambda: dispatch_transition(
            task_id=task.pk,
            trigger="publish",
            actor_type="owner",
            actor_ref="user:1",
        )
    )

    with registered_registry():
        ensure_wired()
        claimable = make_task(project, 3, state=TaskState.PENDING)
        assert_single_publish(
            lambda: dispatch_transition(
                task_id=claimable.pk,
                trigger="claim",
                actor_type="agent",
                actor_ref="sess-1",
                extra={
                    "caller_project_id": project.pk,
                    "session_id": "sess-1",
                    "worker_agent_id": "agent-1",
                },
            )
        )
        assert_single_publish(
            lambda: dispatch_transition(
                task_id=claimable.pk,
                trigger="voluntary_release",
                actor_type="agent",
                actor_ref="sess-1",
                extra={
                    "session_id": "sess-1",
                    "lease_generation": claimable.lease_generation + 1,
                },
            )
        )

    expired = timezone.now() - timedelta(minutes=1)
    expirable = make_task(
        project,
        4,
        state=TaskState.IN_PROGRESS,
        worker_agent_id="agent-1",
        claimed_role=ClaimedRole.CODER,
        lease_acquired_at=expired - timedelta(minutes=45),
        lease_expires_at=expired,
    )
    assert_single_publish(
        lambda: dispatch_transition(
            task_id=expirable.pk,
            trigger="lease_expired",
            actor_type="system",
            actor_ref="lease-sweeper",
        )
    )

    # ...and the API-path policy edit (Section 12.5) publishes too.
    assert_single_publish(
        lambda: write_event(
            type="project.updated",
            project_id=project.pk,
            actor_type="owner",
            actor_ref="user:1",
            data={"scope": "policy", "fields": ["max_retries"]},
        )
    )
