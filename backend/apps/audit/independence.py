"""Auditor independence — G-20 / Section 8.3 invariant 3 (MT-3.3-02).

The single enforcement point for *"the coder session and the auditor
session for one attempt are never the same"* (Section 8.3 rule 3) and
its label half (Section 12.1: *"Same agent audits own work →
``AUDITOR_SAME_AS_CODER`` rule on session and label"*). Called from the
T11 claim guard (inside the claim transaction) **and** re-checked at
verdict time (MT-3.3-05) — one function, never two implementations.

Inputs, all server-side (Section 20.4 / MT-3.3-02 "independence is
server-side"; the claim body's identity is compared, never trusted):

* **Coder session of the current attempt** —
  ``TaskResolution.submitted_by_session`` of the resolution whose
  ``attempt_number`` equals the task's ``attempt_number`` (Section 7.2;
  T7 stores it, and the T7/T8/T10 guards make it impossible to reach
  ``to_be_audited`` without one). This is the field that *survives*
  T7's ``clear_coder_lease`` — the risk note's question answered:
  worker identity is cleared, the submission's session record is not.
* **Coder agent label of the current attempt** — the ``AgentSession``
  row (Section 7.2) the bridge issued for that session: its
  ``agent_label`` is the only plan-defined store of a session's label,
  so the label half resolves through it. When the row is absent (a
  direct-row test fixture; the bridge always creates one in
  production) the *session* half still gates — recorded reading: the
  stricter check runs when its input exists, the comparison is never
  fabricated.

Attempt-scoped by construction (Section 8.3 wording *“for one
attempt”*): the comparison uses only the **current** attempt's
resolution, so a historical coder never blocks a later, independent
auditor — and a fail-closed refusal answers ``AUDITOR_SAME_AS_CODER``
when no current-attempt resolution exists to prove independence from
(FR-AUD-01: independence must be *provable*, never assumed).
"""

from __future__ import annotations

from apps.agents.models import AgentSession
from apps.tasks.models import Task, TaskResolution

from .exceptions import AuditorSameAsCoder


def current_attempt_resolution(task: Task) -> TaskResolution | None:
    """The resolution of *task*'s current attempt, newest first.

    ``None`` means the row carries no submission record for this attempt
    (only reachable by direct-row fixtures — every plan transition into
    ``to_be_audited`` stores one first).
    """
    resolution: TaskResolution | None = (
        TaskResolution.objects.filter(task=task, attempt_number=task.attempt_number)
        .order_by("-submitted_at")
        .first()
    )
    return resolution


def coder_agent_label(resolution: TaskResolution) -> str | None:
    """The coder session's ``agent_label`` (Section 7.2 Agent Session).

    ``None`` when the AgentSession row is not on record — the label
    comparison is then skipped while the session comparison still runs
    (recorded in this module's docstring; production bridges always
    create the row at bootstrap).
    """
    return (
        AgentSession.objects.filter(pk=resolution.submitted_by_session)
        .values_list("agent_label", flat=True)
        .first()
    )


def assert_auditor_independent(
    task: Task,
    *,
    auditor_session_id: str,
    auditor_label: str,
) -> TaskResolution:
    """Refuse unless (*session*, *label*) is independent of the coder.

    Raises the catalog ``AUDITOR_SAME_AS_CODER`` (409) on any match or
    when independence is unprovable; returns the current-attempt
    resolution the verdict path reuses. Called under the task's row
    lock (T11's guard runs inside the claim transaction; the verdict
    service locks before dispatch), so racing claims cannot interleave
    between the comparison and the write (FR-AUD-01).
    """
    resolution = current_attempt_resolution(task)
    if resolution is None:
        raise AuditorSameAsCoder(
            task.pk,
            reason="no resolution on record for the current attempt "
            "(independence cannot be proven)",
        )
    if resolution.submitted_by_session == auditor_session_id:
        raise AuditorSameAsCoder(
            task.pk,
            reason="the auditor session submitted this attempt's resolution",
        )
    label = coder_agent_label(resolution)
    if label is not None and label == auditor_label:
        raise AuditorSameAsCoder(
            task.pk,
            reason=f"the auditor label {auditor_label!r} matches the coder's label",
        )
    return resolution


__all__ = ["assert_auditor_independent", "coder_agent_label", "current_attempt_resolution"]
