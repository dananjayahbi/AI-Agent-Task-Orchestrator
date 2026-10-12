"""MT-1.5-01 — framework smoke tests for the transition registry and guard dispatcher.

Run with ``pytest backend/tests -k state_machine_framework -q``. The suite
proves the *framework* (not the concrete rows — those belong to
MT-1.5-02/03/04): a synthetic ``framework_probe`` row exercises the
generic execution path so these tests never depend on which table rows
exist.

Covered acceptance (MT-1.5-01):

* resolution strictly by the Section 8.2 pair shape; no state outside
  the six canonical names is representable (registration refuses it);
* an unmapped ``(from, trigger)`` pair raises ``TASK_STATE_CONFLICT``
  with HTTP 409 from the closed catalog — before anything is written;
* one successful dispatch performs state change, ``version`` increment,
  the Transition row **and** the Event hook call inside one transaction
  (the rollback test forces the hook to fail and the whole dispatch
  undoes);
* a stale ``expected_version`` answers ``VERSION_CONFLICT`` and changes
  nothing;
* the actor column rejects non-Owner dispatchers with
  ``ROLE_NOT_PERMITTED`` (403);
* the registration extension point (duplicate refused, ``replace=True``
  rewires without touching the dispatcher);
* the Section 9.1 placeholder assertion: no production module writes
  ``state`` outside the state machine (MT-1.5-06 formalizes the scan).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from rest_framework import status

from apps.core.errors import (
    ROLE_NOT_PERMITTED,
    TASK_STATE_CONFLICT,
    VERSION_CONFLICT,
    is_canonical_code,
)
from apps.events.models import Event
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict, TransitionActorForbidden, VersionConflict
from apps.tasks.models import Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.hooks import set_event_hook
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionSpec

from .wp15_helpers import (
    find_state_writes,
    install_event_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)

PROBE_TRIGGER = "framework_probe"


def _probe_spec(*, to_state: str = TaskState.PENDING) -> TransitionSpec:
    """A synthetic row (T99 is structurally valid, no real table row).

    ``reason_code`` must come from the model's catalog — ``publish`` is a
    Section 8.2 trigger code, so the probe exercises the same reason
    validation every real dispatch passes through.
    """
    return TransitionSpec(
        transition_id="T99",
        trigger=PROBE_TRIGGER,
        from_states=frozenset({TaskState.DRAFT}),
        to_state=to_state,
        actor_types=frozenset({"owner"}),
        guard=None,
        side_effect=None,
        event_type="task.transitioned",
        reason_code="publish",
    )


@pytest.fixture(autouse=True)
def registry_guard() -> Iterator[None]:
    """Probe registrations never leak into other suites."""
    with registered_registry():
        yield


@pytest.fixture(autouse=True)
def clean_hooks() -> Iterator[None]:
    """Every dispatch in this suite starts from the default no-op seams."""
    reset_hooks()
    yield
    reset_hooks()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the framework tests."""
    return make_project(name="State machine framework")


def _register_probe(**overrides: Any) -> None:
    DEFAULT_REGISTRY.register(_probe_spec(**overrides), replace=True)


def _dispatch(task: Task, **kwargs: Any) -> Task:
    """Dispatch the probe row for *task* with the Owner actor."""
    payload: dict[str, Any] = {"trigger": PROBE_TRIGGER, "actor_type": "owner"}
    payload.update(kwargs)
    return dispatch_transition(task_id=task.pk, **payload)


def _assert_untouched(task: Task, *, events: list[Mapping[str, Any]] | None = None) -> None:
    """A refusal must leave state, version and history exactly as they were."""
    task.refresh_from_db()
    assert task.state == TaskState.DRAFT
    assert task.version == 1
    assert TaskTransition.objects.filter(task=task).count() == 0
    if events is not None:
        assert events == []


# --- the happy path: one transaction, one history row, one event ------------


def test_dispatch_moves_state_version_history_and_event_in_one_transaction(
    project: Project,
) -> None:
    """Section 8.2 rule 2 in one assertion sweep (FR-TSK-04)."""
    _register_probe()
    events = install_event_recorder()
    task = make_task(project, 1)

    result = _dispatch(task, actor_ref="user:1", note="framework smoke")

    assert result.state == TaskState.PENDING
    assert result.version == 2, "Section 7.2: incremented on every change"

    row = TaskTransition.objects.get(task=task)
    assert (
        row.from_state,
        row.to_state,
        row.actor_type,
        row.actor_ref,
        row.reason_code,
        row.note,
    ) == (TaskState.DRAFT, TaskState.PENDING, "owner", "user:1", "publish", "framework smoke")
    assert row.timestamp is not None, "FR-TSK-04 records when"

    assert len(events) == 1, "exactly one Event row per transition"
    payload = events[0]
    assert payload["type"] == "task.transitioned"
    assert payload["task_id"] == task.pk
    assert payload["actor"] == {"type": "owner", "ref": "user:1"}
    assert payload["data"] == {
        "from_state": TaskState.DRAFT,
        "to_state": TaskState.PENDING,
        "reason_code": "publish",
        "task_version": 2,
    }
    assert payload["_in_atomic_block"] is True, "emitted inside the open transaction"


def test_dispatch_succeeds_while_the_event_hook_is_still_unwired(project: Project) -> None:
    """``reset_hooks`` clears the recorder: the production default answers.

    With WP-1.9 wired, clearing the test override falls back to the
    real writer (`EventsConfig.ready` → `set_default_event_hook`) — the
    dispatch must stay a success path either way (the seam is never a
    blocker; the name records the pre-WP-1.9 era of this test).
    """
    _register_probe()
    reset_hooks()
    task = make_task(project, 1)

    result = _dispatch(task, actor_ref="user:1")

    assert result.state == TaskState.PENDING
    assert TaskTransition.objects.filter(task=task).count() == 1
    assert Event.objects.filter(task_id=task.pk).count() == 1, (
        "the production default writer (WP-1.9) answered — one event per dispatch"
    )


def test_event_hook_failure_rolls_back_state_history_and_event_together(
    project: Project,
) -> None:
    """Forced failure inside the hook undoes the *whole* dispatch."""
    _register_probe()
    attempted: list[Mapping[str, Any]] = []

    def failing_hook(payload: Mapping[str, Any]) -> None:
        attempted.append(payload)
        raise RuntimeError("event writer exploded")

    set_event_hook(failing_hook)
    task = make_task(project, 1)

    with pytest.raises(RuntimeError, match="event writer exploded"):
        _dispatch(task, actor_ref="user:1")

    assert len(attempted) == 1, "the hook ran before the transaction unwound"
    _assert_untouched(task)
    assert TaskTransition.objects.count() == 0, "history and event share the transaction"


# --- refusals: catalog codes, 409, nothing written ---------------------------


def test_unmapped_pair_is_task_state_conflict_409(project: Project) -> None:
    """Section 8.2 rule 1 — wrong from-state answers TASK_STATE_CONFLICT."""
    _register_probe()
    events = install_event_recorder()
    task = make_task(project, 1, state=TaskState.PENDING)

    with pytest.raises(TaskStateConflict) as caught:
        dispatch_transition(
            task_id=task.pk, trigger=PROBE_TRIGGER, actor_type="owner", actor_ref="u"
        )

    assert caught.value.status_code == status.HTTP_409_CONFLICT
    assert caught.value.default_code == TASK_STATE_CONFLICT
    assert is_canonical_code(caught.value.default_code), "closed catalog (20.4 item 5)"
    task.refresh_from_db()
    assert task.state == TaskState.PENDING and task.version == 1
    assert TaskTransition.objects.filter(task=task).count() == 0
    assert events == []


def test_unknown_trigger_is_task_state_conflict(project: Project) -> None:
    """A trigger no row ever registered resolves to the same 409."""
    _register_probe()
    task = make_task(project, 1)

    with pytest.raises(TaskStateConflict):
        dispatch_transition(
            task_id=task.pk, trigger="no_such_row", actor_type="owner", actor_ref="u"
        )

    _assert_untouched(task)


def test_stale_version_is_version_conflict_and_changes_nothing(project: Project) -> None:
    """Section 8.2 rule 3 — the UI's stale version never overwrites."""
    _register_probe()
    events = install_event_recorder()
    task = make_task(project, 1)

    with pytest.raises(VersionConflict) as caught:
        _dispatch(task, actor_ref="u", expected_version=99)

    assert caught.value.status_code == status.HTTP_409_CONFLICT
    assert caught.value.default_code == VERSION_CONFLICT
    _assert_untouched(task, events=events)


def test_wrong_actor_is_role_not_permitted_403(project: Project) -> None:
    """The Actor column rejects agents/system before any guard runs."""
    _register_probe()
    task = make_task(project, 1)

    with pytest.raises(TransitionActorForbidden) as caught:
        _dispatch(task, actor_ref="sess_abc", actor_type="agent")

    assert caught.value.status_code == status.HTTP_403_FORBIDDEN
    assert caught.value.default_code == ROLE_NOT_PERMITTED
    _assert_untouched(task)


def test_non_canonical_actor_type_is_a_programmer_error(project: Project) -> None:
    """Only owner/agent/system exist (Section 7.2) — anything else is a bug."""
    _register_probe()
    task = make_task(project, 1)

    with pytest.raises(ValueError, match="owner/agent/system"):
        _dispatch(task, actor_ref="u", actor_type="auditor")

    _assert_untouched(task)


def test_blank_actor_ref_is_a_programmer_error(project: Project) -> None:
    """FR-TSK-04 records *who* — a dispatch without identity is refused."""
    _register_probe()
    task = make_task(project, 1)

    with pytest.raises(ValueError, match="actor_ref"):
        _dispatch(task, actor_ref="   ")

    _assert_untouched(task)


# --- registration: shape validation and the extension point ------------------


def test_registry_refuses_any_non_canonical_state_or_actor() -> None:
    """FR-TSK-03/ADR-010: only the six states and three actors are representable."""
    base: dict[str, Any] = {
        "transition_id": "T99",
        "trigger": PROBE_TRIGGER,
        "from_states": frozenset({TaskState.DRAFT}),
        "to_state": TaskState.PENDING,
        "actor_types": frozenset({"owner"}),
        "guard": None,
        "side_effect": None,
        "event_type": "task.transitioned",
        "reason_code": "publish",
    }
    for bad_from in (frozenset({"archived"}), frozenset({TaskState.DRAFT, "snoozed"})):
        with pytest.raises(ValueError, match="non-canonical From state"):
            TransitionSpec(**{**base, "from_states": bad_from})

    with pytest.raises(ValueError, match="non-canonical To state"):
        TransitionSpec(**{**base, "to_state": "merged"})

    with pytest.raises(ValueError, match="non-canonical actor"):
        TransitionSpec(**{**base, "actor_types": frozenset({"owner", "auditor"})})


def test_registry_refuses_shapeless_rows() -> None:
    """Empty From sets, non-snake triggers and bad row ids never register."""
    base: dict[str, Any] = {
        "transition_id": "T99",
        "trigger": PROBE_TRIGGER,
        "from_states": frozenset({TaskState.DRAFT}),
        "to_state": TaskState.PENDING,
        "actor_types": frozenset({"owner"}),
        "guard": None,
        "side_effect": None,
        "event_type": "task.transitioned",
        "reason_code": "publish",
    }
    for field, value in (
        ("transition_id", "row-1"),
        ("trigger", "Publish!"),
        ("from_states", frozenset()),
        ("actor_types", frozenset()),
    ):
        with pytest.raises(ValueError):
            TransitionSpec(**{**base, field: value})

    with pytest.raises(ValueError, match="stub must name"):
        TransitionSpec(**{**base, "wired": False})


def test_duplicate_registration_is_refused_unless_replace_is_true() -> None:
    """The extension point is explicit — no silent clobbering."""
    _register_probe()
    with pytest.raises(ValueError, match="already registered"):
        DEFAULT_REGISTRY.register(_probe_spec())

    DEFAULT_REGISTRY.register(_probe_spec(to_state=TaskState.TO_BE_AUDITED), replace=True)
    assert DEFAULT_REGISTRY.get(PROBE_TRIGGER).to_state == TaskState.TO_BE_AUDITED  # type: ignore[union-attr]


def test_replaced_registration_is_what_the_dispatcher_dispatches(project: Project) -> None:
    """Rewiring lands without any dispatcher change (MT-1.5-04 relies on this)."""
    _register_probe(to_state=TaskState.TO_BE_AUDITED)
    task = make_task(project, 1)

    result = _dispatch(task, actor_ref="u")

    assert result.state == TaskState.TO_BE_AUDITED
    assert result.version == 2


# --- Section 9.1 placeholder assertion (formalized by MT-1.5-06) -------------


def test_no_module_outside_the_state_machine_writes_state() -> None:
    """Section 9.1 dependency rule — the placeholder scan of MT-1.5-01."""
    hits = find_state_writes(exclude_parts=("state_machine",))
    assert hits == [], "\n".join(hits)
