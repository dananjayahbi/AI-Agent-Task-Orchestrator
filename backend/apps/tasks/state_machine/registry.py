"""The transition registry: Section 8.2's table as validated data (MT-1.5-01).

A registry row *is* one Section 8.2 table row — ``TransitionSpec`` carries
the row number (``T2`` … ``T19``), the ``From`` set, the ``To`` state
(``None`` for T19's flag-only row, where ``To`` is "archived flag", not a
state), the actors the row accepts, and callables for the guard and
side-effect columns. FR-TSK-03 / ADR-010: **no state outside the six
canonical names is representable** — registration validates every state
against ``TaskState`` and refuses anything else with ``ValueError``
(a programming error, never an API error).

Actors (Section 7.2's ``actor_type`` triple): the letters of
Section 8.2's Actor column map onto it as **O → ``owner``**, **C/A/M →
``agent``**, **S → ``system``** (the Merge Executor row arrives with
WP-3.x and picks its value then). Role distinctions *within* ``agent``
(coder vs auditor) are enforced by the wiring WP's own authorization
checks — the registry stores only the canonical triad so history rows
match Section 7.2 exactly.

Resolution (Section 8.2 rule 1): ``resolve(state, trigger)`` raises the
catalog ``TASK_STATE_CONFLICT`` (409) for any pair the table does not
contain — unknown triggers and wrong-from-states answer identically, so
the matrix test can treat "illegal pair" uniformly.

The registration extension point: ``register(spec, replace=True)`` lets
WP-1.6 (T4/T6), WP-2.6 (T7/T8) and WP-3.x (T10–T18) rewire or add rows
without the dispatcher ever changing (MT-1.5-04 proves the override).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final

from ..exceptions import TaskStateConflict
from ..models.task import Task, TaskState

# Section 7.2 actor_type — exactly three canonical values, none added.
ACTOR_TYPES: Final[tuple[str, ...]] = ("owner", "agent", "system")

# Canonical trigger codes are ADR-010 snake_case machine values (lowercase,
# digits, underscores; no spaces, no display labels).
_TRIGGER_PATTERN: Final = re.compile(r"^[a-z][a-z0-9_]*$")

# Section 8.2 row numbers (T1–T19 today; the shape check allows two digits
# so synthetic test rows stay structurally valid without impersonating a
# real row). T1's create step is the model-level INSERT of MT-1.4-03, not
# a registry row — see the dispatcher docstring's T1 note.
_ROW_PATTERN: Final = re.compile(r"^T(?:[1-9][0-9]?)$")


class TransitionContext:
    """Who is dispatching and what the row's callables may read.

    Carried into every guard and side effect so their signature stays
    stable for later WPs (MT-1.5-04 risk note): the actor identity
    fields identify the caller (FR-TSK-04), and ``extra`` carries
    row-specific inputs the wiring WPs pass through
    ``dispatch_transition(extra=...)`` — a session id for T6's
    ownership guard, resolution data for T7, human-attention evidence
    for T8 — without the dispatcher or this dataclass ever growing new
    fields per transition.
    """

    __slots__ = ("actor_ref", "actor_type", "extra")

    def __init__(
        self,
        *,
        actor_type: str,
        actor_ref: str,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        """Freeze the actor identity; ``extra`` defaults to an empty view."""
        self.actor_type = actor_type
        self.actor_ref = actor_ref
        self.extra: Mapping[str, Any] = extra if extra is not None else {}


# The two callable columns of Section 8.2. Guards raise a catalog
# exception on refusal; side effects mutate the task in memory (or adopt
# a re-fetched row by returning it — see dispatcher).
GuardFn = Callable[[Task, TransitionContext], None]
SideEffectFn = Callable[[Task, TransitionContext], "Task | None"]


@dataclass(frozen=True)
class TransitionSpec:
    """One Section 8.2 row, validated against the canonical catalogs."""

    transition_id: str  # "T2" … "T19" — traceability (Section 20.5)
    trigger: str  # canonical trigger code (ADR-010 machine value)
    from_states: frozenset[str]  # the From column; T19 = all non-completed
    to_state: str | None  # the To column; None = state unchanged (T19)
    actor_types: frozenset[str]  # Section 7.2 actor_type values allowed
    guard: GuardFn | None  # raises the row's catalog error on refusal;
    # None = the table's Guard column reads "None" (T19)
    side_effect: SideEffectFn | None  # the Side effects column
    event_type: str  # Section 9.6 event the dispatcher emits for this row
    reason_code: str  # default history reason (Section 8.4 or trigger code)
    wired: bool = True  # False = stub awaiting its wiring WP (MT-1.5-04)
    stubbed_by: str | None = None  # e.g. "WP-1.6" — the matrix marks stubs

    def __post_init__(self) -> None:
        """Refuse any non-canonical shape (FR-TSK-03; ADR-010; G-01)."""
        if not _ROW_PATTERN.match(self.transition_id):
            raise ValueError(f"{self.transition_id!r} is not a Section 8.2 row id (T1–T19).")
        if not _TRIGGER_PATTERN.match(self.trigger):
            raise ValueError(f"trigger {self.trigger!r} must be a snake_case machine value.")
        if not self.from_states:
            raise ValueError(f"{self.transition_id}: the From column must not be empty.")
        unknown_from = set(self.from_states) - set(TaskState.values)
        if unknown_from:
            raise ValueError(
                f"{self.transition_id}: non-canonical From state(s) {sorted(unknown_from)} "
                f"— the six G-01 states only (FR-TSK-03, ADR-010)."
            )
        if self.to_state is not None and self.to_state not in TaskState.values:
            raise ValueError(
                f"{self.transition_id}: non-canonical To state {self.to_state!r} "
                f"— the six G-01 states only (FR-TSK-03, ADR-010)."
            )
        if not self.actor_types:
            raise ValueError(f"{self.transition_id}: the Actor column must not be empty.")
        unknown_actors = set(self.actor_types) - set(ACTOR_TYPES)
        if unknown_actors:
            raise ValueError(
                f"{self.transition_id}: non-canonical actor(s) {sorted(unknown_actors)} "
                f"— owner/agent/system only (Section 7.2)."
            )
        if self.wired and self.stubbed_by is not None:
            raise ValueError(f"{self.transition_id}: stubbed_by marks a stub (wired=False).")
        if not self.wired and self.stubbed_by is None:
            raise ValueError(f"{self.transition_id}: a stub must name the wiring WP.")

    @property
    def is_flag_only(self) -> bool:
        """T19's shape: the row fires without moving between states."""
        return self.to_state is None


class TransitionRegistry:
    """Keyed by trigger; the From column is validated per dispatch.

    Triggers are unique across the table (Section 8.2 gives each row its
    own trigger), so one lookup returns the row and the From-set check
    yields the pair decision — exactly the (from_state, trigger) shape
    MT-1.5-01 requires, and a data change when WP-3.x adds rows.
    """

    def __init__(self) -> None:
        """Empty by default; ``loader.ensure_registered`` fills it once."""
        self._by_trigger: dict[str, TransitionSpec] = {}

    def register(self, spec: TransitionSpec, *, replace: bool = False) -> None:
        """The extension point: add (or rewire) one table row.

        A duplicate trigger without ``replace=True`` is a programming
        error (``ValueError``) — silent last-write-wins would let a wiring
        WP clobber another WP's row without saying so.
        """
        existing = self._by_trigger.get(spec.trigger)
        if existing is not None and not replace:
            raise ValueError(
                f"trigger {spec.trigger!r} is already registered as "
                f"{existing.transition_id}; pass replace=True to rewire it."
            )
        self._by_trigger[spec.trigger] = spec

    def resolve(self, *, task_id: str, state: str, trigger: str) -> TransitionSpec:
        """Return the row for ``(state, trigger)`` or answer 409.

        Section 8.2 rule 1: an unmapped pair — unknown trigger *or*
        from-state outside the row's From column — is a
        ``TASK_STATE_CONFLICT`` (HTTP 409) from the closed catalog.
        """
        spec = self._by_trigger.get(trigger)
        if spec is None or state not in spec.from_states:
            raise TaskStateConflict(
                task_id,
                reason=f"cannot fire '{trigger}' from state '{state}' (no such transition)",
            )
        return spec

    def get(self, trigger: str) -> TransitionSpec | None:
        """Look a row up by trigger regardless of From state (tests, tools)."""
        return self._by_trigger.get(trigger)

    def specs(self) -> dict[str, TransitionSpec]:
        """A copy keyed by trigger — matrix enumeration and test snapshots."""
        return dict(self._by_trigger)

    def replace_all(self, specs: Mapping[str, TransitionSpec]) -> None:
        """Restore a snapshot (test fixtures); the dispatcher never calls it."""
        self._by_trigger = dict(specs)


#: The process-wide registry the dispatcher resolves against.
DEFAULT_REGISTRY: Final = TransitionRegistry()
