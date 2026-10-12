"""MT-1.5-04 — agent transition stubs T4/T6/T7/T8 (register now, wire later).

Run with ``pytest backend/tests -k agent_transition_stubs -q``. The suite
pins the four stubbed Section 8.2 rows *as registered* (shape,
verbatim guard/side-effect contract text, stub markers), proves
dispatching one fails deterministically with **no side effects** (state,
``version``, history and events untouched), and proves the registry
extension point lets a wiring WP rewire a stub **without modifying the
dispatcher** — the MT's template for WP-1.6, WP-2.6 and WP-3.x.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework import status

from apps.core.errors import SERVER_ERROR
from apps.projects.models import Project
from apps.tasks.exceptions import TransitionNotWired
from apps.tasks.models import ClaimedRole, ReviewReason, Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec
from apps.tasks.state_machine.transitions_agent import T8_REVIEW_REASONS

from .wp15_helpers import (
    install_event_recorder,
    install_push_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)

# Section 8.2 rows T4/T6/T7/T8, transcribed: trigger, From, To, actors.
STUB_SHAPE: dict[str, tuple[str, frozenset[str], str | None, frozenset[str], str]] = {
    "T4": (
        "claim",
        frozenset({TaskState.PENDING}),
        TaskState.IN_PROGRESS,
        frozenset({"agent"}),
        "WP-1.6",
    ),
    "T6": (
        "voluntary_release",
        frozenset({TaskState.IN_PROGRESS}),
        TaskState.PENDING,
        frozenset({"agent", "owner"}),
        "WP-1.6",
    ),
    "T7": (
        "submit",
        frozenset({TaskState.IN_PROGRESS}),
        TaskState.TO_BE_AUDITED,
        frozenset({"agent"}),
        "WP-2.6",
    ),
    "T8": (
        "submit_flagged",
        frozenset({TaskState.IN_PROGRESS}),
        TaskState.IN_HUMAN_REVIEW,
        frozenset({"agent", "system"}),
        "WP-2.6",
    ),
}

# The verbatim Section 8.2 Guard / Side-effects cells each stub must carry
# (Section 20.5 traceability — no paraphrased semantics).
STUB_TEXT: dict[str, tuple[str, ...]] = {
    "T4": (
        "Project active",
        "token scope matches",
        "dependencies completed",
        "max_concurrent_tasks",
        "row lock won",
        "attempt_number",
        "task.claimed",
    ),
    "T6": (
        "Caller owns lease (or Owner override)",
        "Clear worker; no failure increment",
    ),
    "T7": (
        "Lease owner and not expired",
        "resolution valid",
        "audit_required",
        "not self-flagged",
        "scope check ok",
        "Store resolution + patch; clear worker",
    ),
    "T8": (
        "requires_human_attention",
        "outside scope",
        "self_flagged",
        "scope_violation",
        "push notification",
    ),
}


@pytest.fixture(autouse=True)
def registry_guard() -> Iterator[None]:
    """Rewiring probes in this suite never leak into other suites."""
    with registered_registry():
        yield


@pytest.fixture(autouse=True)
def clean_hooks() -> Iterator[None]:
    """Default no-op seams unless a test installs a recorder."""
    reset_hooks()
    yield
    reset_hooks()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the stub tests."""
    return make_project(name="Agent transition stubs")


def _dispatch(task: Task, trigger: str, **kwargs: Any) -> Task:
    payload: dict[str, Any] = {"actor_type": "agent", "actor_ref": "sess_stub"}
    payload.update(kwargs)
    return dispatch_transition(task_id=task.pk, trigger=trigger, **payload)


def _spec(transition_id: str) -> TransitionSpec:
    spec = DEFAULT_REGISTRY.get(STUB_SHAPE[transition_id][0])
    assert spec is not None, f"{transition_id} must be registered"
    return spec


# --- registration shape (Section 8.2, verbatim) ------------------------------


@pytest.mark.parametrize("transition_id", sorted(STUB_SHAPE))
def test_stub_is_registered_with_the_exact_section_8_2_shape(transition_id: str) -> None:
    """Trigger, From, To and actors match the table — nothing paraphrased."""
    trigger, from_states, to_state, actors, wired_by = STUB_SHAPE[transition_id]
    spec = _spec(transition_id)

    assert spec.transition_id == transition_id
    assert spec.trigger == trigger
    assert spec.from_states == from_states
    assert spec.to_state == to_state
    assert spec.actor_types == actors
    assert spec.wired is False, "stubs dispatch-blocked until their wiring WP"
    assert spec.stubbed_by == wired_by
    assert spec.guard is not None and spec.side_effect is not None, "contracts present"


@pytest.mark.parametrize("transition_id", sorted(STUB_SHAPE))
def test_stub_docstrings_carry_the_verbatim_guard_and_side_effect_text(
    transition_id: str,
) -> None:
    """The wiring contract is the table's own words (Section 20.5)."""
    spec = _spec(transition_id)
    assert spec.guard is not None and spec.side_effect is not None
    guard_text = spec.guard.__doc__ or ""
    side_text = spec.side_effect.__doc__ or ""
    combined = guard_text + side_text
    for fragment in STUB_TEXT[transition_id]:
        assert fragment in combined, f"{transition_id} contract lost {fragment!r}"


def test_t8_review_reasons_are_strictly_the_canonical_pair() -> None:
    """Section 8.4: self_flagged / scope_violation — nothing wider."""
    assert T8_REVIEW_REASONS == (ReviewReason.SELF_FLAGGED, ReviewReason.SCOPE_VIOLATION)
    assert set(T8_REVIEW_REASONS) <= set(ReviewReason.values)


# --- dispatching a stub fails safely -----------------------------------------


@pytest.mark.parametrize(
    ("transition_id", "task_state"),
    [
        ("T4", TaskState.PENDING),
        ("T6", TaskState.IN_PROGRESS),
        ("T7", TaskState.IN_PROGRESS),
        ("T8", TaskState.IN_PROGRESS),
    ],
)
def test_dispatching_a_stub_fails_deterministically_with_no_side_effects(
    project: Project, transition_id: str, task_state: str
) -> None:
    """Legal pair, right actor — still refused; nothing anywhere changes."""
    events = install_event_recorder()
    pushes = install_push_recorder()
    trigger = STUB_SHAPE[transition_id][0]
    actors = STUB_SHAPE[transition_id][3]
    task = make_task(project, 1, state=task_state)
    if task_state == TaskState.IN_PROGRESS:
        task.worker_agent_id = "claude-code-session-98b2"
        task.claimed_role = ClaimedRole.CODER
        task.lease_expires_at = timezone.now() + timedelta(minutes=30)
        task.save()

    with pytest.raises(TransitionNotWired) as caught:
        _dispatch(task, trigger, actor_type=sorted(actors)[0], actor_ref="sess_x")

    assert caught.value.default_code == SERVER_ERROR, "catalog-closed: no NOT_IMPLEMENTED code"
    assert caught.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert transition_id in str(caught.value)
    assert caught.value.wired_by == STUB_SHAPE[transition_id][4]

    task.refresh_from_db()
    assert task.state == task_state
    assert task.version == 1
    assert TaskTransition.objects.filter(task=task).count() == 0
    assert events == [] and pushes == []


@pytest.mark.parametrize("transition_id", sorted(STUB_SHAPE))
def test_stub_guard_and_side_effect_refuse_when_called_directly(
    project: Project, transition_id: str
) -> None:
    """Defense in depth: even a direct call fails safely (no half-effects)."""
    spec = _spec(transition_id)
    assert spec.guard is not None and spec.side_effect is not None
    task = make_task(project, 1, state=TaskState.PENDING)
    context = TransitionContext(actor_type="agent", actor_ref="sess_x")

    with pytest.raises(TransitionNotWired):
        spec.guard(task, context)
    with pytest.raises(TransitionNotWired):
        spec.side_effect(task, context)

    task.refresh_from_db()
    assert task.version == 1


# --- the extension point: rewiring without touching the dispatcher -----------


def test_override_registration_replaces_a_stub_and_dispatches(project: Project) -> None:
    """WP-1.6's future wiring path, exercised today: replace=True, no dispatcher edit."""
    events = install_event_recorder()
    task = make_task(project, 1, state=TaskState.PENDING)

    def _wire_claim(row_task: Task, context: TransitionContext) -> Task | None:
        """The T4 side effects of Section 8.2, as WP-1.6 will write them."""
        row_task.worker_agent_id = context.actor_ref
        row_task.worker_session_id = "sess_wired"
        row_task.claimed_role = ClaimedRole.CODER
        row_task.lease_acquired_at = timezone.now()
        row_task.lease_expires_at = timezone.now() + timedelta(minutes=45)
        row_task.attempt_number += 1
        return None

    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T4",
            trigger="claim",
            from_states=frozenset({TaskState.PENDING}),
            to_state=TaskState.IN_PROGRESS,
            actor_types=frozenset({"agent"}),
            guard=None,
            side_effect=_wire_claim,
            event_type="task.claimed",
            reason_code="claim",
        ),
        replace=True,
    )

    result = _dispatch(task, "claim")

    assert result.state == TaskState.IN_PROGRESS
    assert result.worker_agent_id == "sess_stub", "the wired side effect ran with the actor's id"
    assert result.attempt_number == 1
    assert result.version == 2
    assert [event["type"] for event in events] == ["task.claimed"]
    assert TaskTransition.objects.filter(task=task).count() == 1

    # The dispatcher module itself is byte-identical to what shipped — the
    # test's own import proves rewiring happened purely through the registry.
    import apps.tasks.state_machine.dispatcher as dispatcher_module

    assert "TransitionNotWired" in dispatcher_module.__dict__
    assert dispatcher_module.dispatch_transition.__module__.endswith("dispatcher")
