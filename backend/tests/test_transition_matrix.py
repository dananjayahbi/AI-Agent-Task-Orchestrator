"""MT-1.5-06 — exhaustive transition matrix: every legal pair passes, every illegal pair 409s.

Run with ``pytest backend/tests -k transition_matrix -q`` plus the
coverage gate
``pytest backend/tests -k transition_matrix --cov=apps.tasks.state_machine --cov-fail-under=85``.

The matrix is **generated from the registry**, not hand-copied (risk
note): collection imports the dispatcher, registers the default rows
once, and parametrizes every ``(state, registered trigger)`` pair —
9 triggers × 6 states = 54 cases, asserted exhaustive by
``test_matrix_is_exhaustive``. The Section 8.2 *shape* of each row is
still pinned literally (:data:`EXPECTED_TABLE`) so drift between the
registry and the plan fails a named test, while pair enumeration can
never drift from what the dispatcher will actually resolve.

Also asserted here (the MT's remaining acceptance):

* stub rows (T4/T6/T7/T8) show up in the matrix as their not-wired
  failure path, marked for WP-1.15's re-check;
* Section 8.3 invariants at dispatch time: no transition to
  ``completed`` without ``merge_status = merged`` (OQ-06's manual
  exception included), no coder lease outside ``in_progress``,
  ``in_progress`` only ever *with* worker/lease fields;
* the direct-write rule (Section 9.1): the production-code scan finds
  ``state`` writes **only** inside the state machine — and the scan
  itself is self-tested so a vacuous pass is impossible.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework import status

from apps.core.errors import TASK_STATE_CONFLICT
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict, TransitionNotWired
from apps.tasks.models import ClaimedRole, Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec

from .wp15_helpers import (
    SECTION_9_6_EVENTS,
    STATE_WRITE_PATTERNS,
    find_state_writes,
    install_event_recorder,
    install_push_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)

# The six canonical states in lifecycle order (Section 8.1).
CANONICAL_STATES: tuple[str, ...] = (
    "draft",
    "pending",
    "in_progress",
    "to_be_audited",
    "in_human_review",
    "completed",
)

# Section 8.2 rows T2–T19 that WP-1.5 registers, transcribed literally:
# trigger -> (From set, To, Actor set). Enumerated pairs below come from
# the registry; this dict pins the *shape* for traceability (Section 20.5).
EXPECTED_TABLE: dict[str, tuple[frozenset[str], str | None, frozenset[str]]] = {
    "publish": (frozenset({"draft"}), "pending", frozenset({"owner"})),
    "unpublish": (frozenset({"pending"}), "draft", frozenset({"owner"})),
    "claim": (frozenset({"pending"}), "in_progress", frozenset({"agent"})),
    "lease_expired": (frozenset({"in_progress"}), "pending", frozenset({"system"})),
    "voluntary_release": (
        frozenset({"in_progress"}),
        "pending",
        frozenset({"agent", "owner"}),
    ),
    "submit": (frozenset({"in_progress"}), "to_be_audited", frozenset({"agent"})),
    "submit_flagged": (
        frozenset({"in_progress"}),
        "in_human_review",
        frozenset({"agent", "system"}),
    ),
    "retry_exhausted": (
        frozenset({"in_progress"}),
        "in_human_review",
        frozenset({"system"}),
    ),
    "archive": (
        frozenset({"draft", "pending", "in_progress", "to_be_audited", "in_human_review"}),
        None,  # archived flag — never a seventh state (Section 8.1)
        frozenset({"owner"}),
    ),
}

# One dispatcher actor per trigger for the matrix run (each pair is asked
# by an actor the Actor column admits, so refusals are *state* refusals).
ACTOR_FOR_TRIGGER: dict[str, str] = {
    "publish": "owner",
    "unpublish": "owner",
    "claim": "agent",
    "lease_expired": "system",
    "voluntary_release": "agent",
    "submit": "agent",
    "submit_flagged": "agent",
    "retry_exhausted": "system",
    "archive": "owner",
}

ensure_registered()
SPECS: dict[str, TransitionSpec] = DEFAULT_REGISTRY.specs()


LEGAL_CASES: list[Any] = [
    pytest.param(
        trigger,
        state,
        id=f"{spec.transition_id}:{state}:{trigger}",
    )
    for trigger, spec in sorted(SPECS.items(), key=lambda item: item[1].transition_id)
    for state in CANONICAL_STATES
    if state in spec.from_states
]
ILLEGAL_CASES: list[Any] = [
    pytest.param(
        trigger,
        state,
        id=f"{spec.transition_id}:{state}:{trigger}",
    )
    for trigger, spec in sorted(SPECS.items(), key=lambda item: item[1].transition_id)
    for state in CANONICAL_STATES
    if state not in spec.from_states
]


@pytest.fixture(autouse=True)
def registry_guard() -> Iterator[None]:
    """Invariant probes registered here never leak into other suites."""
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
    """One project row for the matrix."""
    return make_project(name="Transition matrix")


def _prepare(project: Project, *, state: str, trigger: str) -> Task:
    """A task in *state* with whatever the row's own premises require.

    Only premises the wired guards read are staged here (expired lease
    for T5, policy-limit failures for T9); stub rows refuse before their
    guards, so they receive only a realistic ``in_progress`` shape.
    ``in_progress`` tasks always carry the coder lease (Section 8.3
    rule 1) so T19's post-transition invariant runs honestly.
    """
    task = make_task(project, 1, state=state)
    changed = False
    if state == TaskState.IN_PROGRESS:
        task.worker_agent_id = "claude-code-session-98b2"
        task.worker_session_id = "sess_7f3c91d0a2b44e"
        task.claimed_role = ClaimedRole.CODER
        task.lease_acquired_at = timezone.now() - timedelta(minutes=10)
        task.lease_expires_at = timezone.now() + timedelta(minutes=35)
        changed = True
    if trigger == "lease_expired":
        task.lease_expires_at = timezone.now() - timedelta(minutes=1)
        changed = True
    if trigger == "retry_exhausted":
        task.failure_retry_count = project.agent_policy.max_retries
        changed = True
    if changed:
        task.save()
    return task


def _dispatch(task: Task, trigger: str) -> Task:
    return dispatch_transition(
        task_id=task.pk,
        trigger=trigger,
        actor_type=ACTOR_FOR_TRIGGER[trigger],
        actor_ref="matrix-actor",
    )


def _assert_untouched(
    task: Task,
    state: str,
    *,
    events: list[Any],
    pushes: list[Any],
) -> None:
    task.refresh_from_db()
    assert task.state == state
    assert task.version == 1
    assert TaskTransition.objects.filter(task=task).count() == 0
    assert events == [] and pushes == []


# --- exhaustiveness and shape -------------------------------------------------


def test_matrix_is_exhaustive_over_states_and_registered_triggers() -> None:
    """9 registered triggers × 6 canonical states = 54 parametrized cases."""
    assert len(SPECS) == 9, sorted(SPECS)
    assert len(CANONICAL_STATES) == 6
    assert len(LEGAL_CASES) == 13, [case.values for case in LEGAL_CASES]
    assert len(ILLEGAL_CASES) == 41, [case.values for case in ILLEGAL_CASES]
    assert len(LEGAL_CASES) + len(ILLEGAL_CASES) == len(SPECS) * len(CANONICAL_STATES)


def test_registry_shape_matches_section_8_2_transcription() -> None:
    """From/To/Actor of every registered row equals the plan's table."""
    assert set(SPECS) == set(EXPECTED_TABLE)
    for trigger, spec in SPECS.items():
        from_states, to_state, actors = EXPECTED_TABLE[trigger]
        assert spec.from_states == from_states, trigger
        assert spec.to_state == to_state, trigger
        assert spec.actor_types == actors, trigger
        assert set(spec.from_states) <= set(TaskState.values), "ADR-010 canonical"
        assert spec.to_state is None or spec.to_state in TaskState.values
        assert spec.event_type in SECTION_9_6_EVENTS, "Section 9.6 catalog (20.4 item 6)"


def test_matrix_marks_stubbed_transitions_for_later_wps() -> None:
    """Stubs are flagged (not-wired) so WP-1.15 can re-check their wiring."""
    stubs = {spec.transition_id for spec in SPECS.values() if not spec.wired}
    wired = {spec.transition_id for spec in SPECS.values() if spec.wired}
    assert stubs == {"T4", "T6", "T7", "T8"}
    assert wired == {"T2", "T3", "T5", "T9", "T19"}
    assert all(spec.stubbed_by for spec in SPECS.values() if not spec.wired), (
        "each stub names its wiring WP"
    )


# --- legal pairs: one passing test each --------------------------------------


@pytest.mark.parametrize(("trigger", "state"), LEGAL_CASES)
def test_legal_pair_dispatches_with_side_effects_and_one_history_row(
    project: Project, trigger: str, state: str
) -> None:
    """Every legal pair passes: target state, bump, one row, one event."""
    spec = SPECS[trigger]
    events = install_event_recorder()
    pushes = install_push_recorder()
    task = _prepare(project, state=state, trigger=trigger)

    if not spec.wired:
        with pytest.raises(TransitionNotWired):
            _dispatch(task, trigger)
        _assert_untouched(task, state, events=events, pushes=pushes)
        return

    result = _dispatch(task, trigger)

    expected_state = spec.to_state if spec.to_state is not None else state
    assert result.state == expected_state
    assert result.version == 2

    rows = list(TaskTransition.objects.filter(task=task))
    assert len(rows) == 1, "exactly one history row (FR-TSK-04)"
    row = rows[0]
    assert (row.from_state, row.to_state) == (state, expected_state)
    assert row.actor_type == ACTOR_FOR_TRIGGER[trigger]
    assert row.actor_ref == "matrix-actor"
    assert row.reason_code == spec.reason_code
    assert row.timestamp is not None

    # One event per transition row, plus the WP-3.9 review.requested on
    # in_human_review entry (MT-3.9-02 — exactly one per entry).
    expected_events = 2 if spec.to_state == TaskState.IN_HUMAN_REVIEW else 1
    assert len(events) == expected_events, "one event per transition (+ entry event)"
    assert events[0]["type"] == spec.event_type
    assert events[0]["data"]["task_version"] == 2
    if spec.to_state == TaskState.IN_HUMAN_REVIEW:
        assert events[1]["type"] == "review.requested", "MT-3.9-02 exactly one per entry"
        assert events[1]["_in_atomic_block"] is True

    expected_pushes = 1 if spec.to_state == TaskState.IN_HUMAN_REVIEW else 0
    assert len(pushes) == expected_pushes, "Section 9.8: push on in_human_review entry"

    if trigger == "archive":
        assert result.archived_at is not None, "T19's side effect (flag set)"
        assert result.state == state, "T19 changes no state"
    if spec.to_state == TaskState.IN_PROGRESS:
        assert result.claimed_role == ClaimedRole.CODER, "Section 8.3 rule 1, positive half"


# --- illegal pairs: 409 + zero side effects each ------------------------------


@pytest.mark.parametrize(("trigger", "state"), ILLEGAL_CASES)
def test_illegal_pair_is_task_state_conflict_409_with_no_side_effects(
    project: Project, trigger: str, state: str
) -> None:
    """Every illegal pair answers TASK_STATE_CONFLICT (409) and writes nothing."""
    events = install_event_recorder()
    pushes = install_push_recorder()
    task = _prepare(project, state=state, trigger=trigger)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, trigger)

    assert caught.value.status_code == status.HTTP_409_CONFLICT
    assert caught.value.default_code == TASK_STATE_CONFLICT
    _assert_untouched(task, state, events=events, pushes=pushes)


# --- Section 8.3 invariants at dispatch time ---------------------------------


def _probe(
    *,
    trigger: str,
    from_states: frozenset[str],
    to_state: str | None,
    side_effect: Any = None,
) -> None:
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T99",
            trigger=trigger,
            from_states=from_states,
            to_state=to_state,
            actor_types=frozenset({"owner"}),
            guard=None,
            side_effect=side_effect,
            event_type="task.transitioned",
            reason_code="publish",
        ),
        replace=True,
    )


def test_invariant_completed_needs_merged_status(project: Project) -> None:
    """Section 8.3 rule 2 — no ``completed`` without ``merged`` (OQ-06 caveat)."""
    _probe(
        trigger="complete_probe",
        from_states=frozenset({TaskState.PENDING}),
        to_state=TaskState.COMPLETED,
    )
    task = make_task(project, 1, state=TaskState.PENDING)

    with pytest.raises(TaskStateConflict) as caught:
        dispatch_transition(
            task_id=task.pk, trigger="complete_probe", actor_type="owner", actor_ref="u"
        )
    assert "Section 8.3 rule 2" in str(caught.value)
    task.refresh_from_db()
    assert task.state == TaskState.PENDING and task.version == 1
    assert TaskTransition.objects.filter(task=task).count() == 0

    task.merge_status = "merged"
    task.save()
    result = dispatch_transition(
        task_id=task.pk, trigger="complete_probe", actor_type="owner", actor_ref="u"
    )
    assert result.state == TaskState.COMPLETED and result.version == 2


def test_invariant_completed_allowed_without_a_merge_step(project: Project) -> None:
    """OQ-06 decided: merge_strategy ``manual`` completes without an executor."""
    policy = project.agent_policy
    policy.merge_strategy = "manual"
    policy.save()
    _probe(
        trigger="complete_probe",
        from_states=frozenset({TaskState.PENDING}),
        to_state=TaskState.COMPLETED,
    )
    task = make_task(project, 1, state=TaskState.PENDING)

    result = dispatch_transition(
        task_id=task.pk, trigger="complete_probe", actor_type="owner", actor_ref="u"
    )

    assert result.state == TaskState.COMPLETED


def test_invariant_no_coder_lease_outside_in_progress(project: Project) -> None:
    """Section 8.3 rule 1 — leaving ``in_progress`` must clear the worker."""
    task = _prepare(project, state=TaskState.IN_PROGRESS, trigger="noop")
    original_worker = task.worker_agent_id

    def _leaky(row_task: Task, context: TransitionContext) -> Task | None:
        """Deliberately wrong wiring: leaves the coder lease behind."""
        return None

    _probe(
        trigger="leaseleak_probe",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.PENDING,
        side_effect=_leaky,
    )

    with pytest.raises(TaskStateConflict) as caught:
        dispatch_transition(
            task_id=task.pk, trigger="leaseleak_probe", actor_type="owner", actor_ref="u"
        )
    assert "Section 8.3 rule 1" in str(caught.value)

    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS, "the refusal rolled back"
    assert task.worker_agent_id == original_worker
    assert task.version == 1 and TaskTransition.objects.filter(task=task).count() == 0

    def _clearing(row_task: Task, context: TransitionContext) -> Task | None:
        """Correct wiring: clear the coder lease on the way out."""
        row_task.worker_agent_id = None
        row_task.worker_session_id = None
        row_task.claimed_role = None
        row_task.lease_acquired_at = None
        row_task.lease_expires_at = None
        return None

    _probe(
        trigger="leaseleak_probe",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.PENDING,
        side_effect=_clearing,
    )
    result = dispatch_transition(
        task_id=task.pk, trigger="leaseleak_probe", actor_type="owner", actor_ref="u"
    )
    assert result.state == TaskState.PENDING and result.claimed_role is None


def test_invariant_entering_in_progress_requires_the_lease_shape(project: Project) -> None:
    """Section 8.3 rule 1, positive half — no workerless ``in_progress`` rows."""
    _probe(
        trigger="noworker_probe",
        from_states=frozenset({TaskState.PENDING}),
        to_state=TaskState.IN_PROGRESS,
    )
    task = make_task(project, 1, state=TaskState.PENDING)

    with pytest.raises(TaskStateConflict) as caught:
        dispatch_transition(
            task_id=task.pk, trigger="noworker_probe", actor_type="owner", actor_ref="u"
        )
    assert "Section 8.3 rule 1" in str(caught.value)
    task.refresh_from_db()
    assert task.state == TaskState.PENDING and task.version == 1


# --- Section 9.1 direct-write rule -------------------------------------------


def test_state_writes_exist_only_inside_the_state_machine() -> None:
    """The service is the sole writer of ``state`` across production code."""
    hits = find_state_writes()
    assert hits, "the dispatcher's assignment must be visible to the scan"
    for hit in hits:
        assert hit.startswith("tasks/state_machine/dispatcher.py:"), hit
    assert len(hits) == 1, "exactly one writer: the dispatcher's to-state assignment"


def test_the_state_write_scan_itself_catches_writes_and_spares_clean_code() -> None:
    """Self-test — the scan cannot pass vacuously (false negatives/positives)."""
    dirty = (
        "task.state = 'pending'",
        'locked.update(state="draft")',
        "Task.objects.bulk_update(rows, ['state'])",
        "task.state = task.state  # a self-assignment is still a write",
    )
    clean = (
        "task.state == state",
        "state = models.CharField(choices=TaskState.choices)",
        ".exclude(depends_on__state=TaskState.COMPLETED)",
    )
    for sample in dirty:
        assert any(pattern.search(sample) for pattern in STATE_WRITE_PATTERNS), sample
    for sample in clean:
        assert not any(pattern.search(sample) for pattern in STATE_WRITE_PATTERNS), sample


def test_the_scan_runs_over_the_whole_production_tree() -> None:
    """Scope guard: the scan really reads backend/apps (not an empty glob)."""
    from .wp15_helpers import APPS_ROOT

    modules = list(APPS_ROOT.rglob("*.py"))
    assert len(modules) > 50, "apps tree not scanned as expected"
    assert any("tasks" in path.parts for path in modules)
