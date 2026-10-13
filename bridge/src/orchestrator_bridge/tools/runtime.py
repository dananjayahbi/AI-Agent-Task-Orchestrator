"""The session-bound runtime every core-tool handler reads (Sections 10.3,
10.5; MT-2.2-04, MT-2.4-02…06).

One object per bridge process, built at startup from the pieces Section 10.3
produces: the validated binding (manifest), the shared :class:`ApiClient`,
and the opened :class:`~orchestrator_bridge.session.AgentSession`. Handlers
never see ``Settings`` or tokens — the runtime is their whole world, which is
also what makes the handlers trivially testable (a fake client, a fixed
session).

It also owns the two pieces of *process-memory* state the tools need:

* **project-context cache** — served by ``get_project_context`` with zero
  network calls once populated (MT-2.4-06); the miss path refreshes through
  the client, so a resumed session (future HTTP mode) self-heals.
* **lease generations** — the ADR-012 fencing half recorded from each
  successful claim so ``release_task`` can carry ``lease_generation``. Never
  persisted; a restarted bridge legitimately re-derives it from a new claim
  (the backend stays the authority — Section 19.3).
* **submission spool** — the MT-2.6-05 durability seam :mod:`submit` writes
  to before every upload (Section 10.10). The entrypoints bind the
  user-level spool at startup; a runtime without one (bare unit tests)
  rejects submissions with a structured wiring failure rather than risking
  an undurable upload.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..manifest import StartupBinding
from ..session import AgentSession, ProjectContext, fetch_project_context
from ..submission_spool import SubmissionSpool
from ..transport import ApiClient

__all__ = ["ToolRuntime"]


@dataclass(slots=True)
class ToolRuntime:
    """Bound session state for the core tools (one per process)."""

    binding: StartupBinding
    client: ApiClient
    session: AgentSession
    context: ProjectContext | None = field(default=None, repr=False)
    spool: SubmissionSpool | None = field(default=None, repr=False)
    #: Section 10.4 step 2: the startup-configured session capability
    #: (``vision``/``text_only``/unset = ``unknown``); read by
    #: ``read_task_attachment``'s resolver — never inferred (ADR-006).
    session_capability: str | None = None
    _lease_generations: dict[str, int] = field(default_factory=dict, repr=False)

    @classmethod
    def from_session(
        cls,
        binding: StartupBinding,
        client: ApiClient,
        session: AgentSession,
        *,
        spool: SubmissionSpool | None = None,
        session_capability: str | None = None,
    ) -> ToolRuntime:
        """Bind an opened session; the startup cache is already populated."""
        return cls(
            binding=binding,
            client=client,
            session=session,
            context=session.context,
            spool=spool,
            session_capability=session_capability,
        )

    @property
    def project_id(self) -> str:
        """The bound project — never a tool argument (Section 10.3)."""
        return self.binding.project_id

    @property
    def agent_session_id(self) -> str:
        """The backend session id every claim/release carries (G-18)."""
        return self.session.agent_session_id

    def project_context(self) -> ProjectContext:
        """Cached context; a ``None`` cache (resumed session) fetches once.

        The cache hit performs no backend request — that is what makes the
        orientation call cheap (MT-2.4-06). A backend failure on the miss
        path surfaces as the client's typed ``ApiError`` (translated by the
        tool boundary into a structured retryable error), never a crash.
        """
        if self.context is None:
            self.context = fetch_project_context(self.client, self.binding)
        return self.context

    def record_lease(self, task_id: str, lease_generation: int) -> None:
        """Remember the fencing generation returned by a successful claim."""
        self._lease_generations[task_id] = lease_generation

    def lease_generation(self, task_id: str) -> int | None:
        """The last generation claimed for *task_id* (None = never claimed here).

        Release still proceeds without it — the backend answers
        ``LEASE_NOT_OWNED``/``LEASE_EXPIRED`` authoritatively rather than the
        bridge guessing locally (Section 19.3).
        """
        return self._lease_generations.get(task_id)
