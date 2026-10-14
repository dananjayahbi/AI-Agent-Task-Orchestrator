"""``orchestrator:audit`` prompt (parent plan Sections 10.7, 11.2, 9.4,
12.1; FR-MCP-04; MT-2.8-04).

The auditor workflow — the five Section 10.7 steps in plan order (claim,
check out branch, run matrix, review diff vs criteria, submit verdict),
mirroring Section 11.2 step for step. Independence is stated up front
(auditor session differs from coder session; ``AUDITOR_SAME_AS_CODER`` —
Section 12.1 self-approval mitigation), the branch stays read-only (Sections
11.2 step 4, 10.8), the verdict vocabulary is exactly the Section 10.5
schema (``pass`` / ``flag_risk`` / ``fail``, confidence 1–5), and the
backend's Policy Engine — not the verdict text — decides the task's final
state (Section 9.4; ADR-009; MT-2.8-04 risk note: wording stays "submit
verdict", never "complete the task"). The workflow works without the
prompt (NFR-08, ADR-011): tool descriptions and the auditor rules block
carry the same obligations.
"""

from __future__ import annotations

from typing import Final

__all__ = ["DESCRIPTION", "NAME", "TEXT"]

NAME: Final = "orchestrator:audit"

DESCRIPTION: Final = (
    "Auditor workflow: claim, check out branch, run matrix, review diff vs "
    "criteria, submit verdict (Section 10.7)."
)

TEXT: Final = (
    "Optional guidance for auditing one task (Section 10.7). Independence "
    "is mandatory: your auditor session must be a different session from "
    "the coder's — the backend rejects a same-session verdict with "
    "AUDITOR_SAME_AS_CODER (Section 12.1).\n"
    "\n"
    "1. Claim: call get_available_tasks with role auditor, then claim_task "
    "with role auditor on one to_be_audited task. TASK_ALREADY_CLAIMED "
    "means another auditor holds it — pick another.\n"
    "2. Check out the branch read-only: inspect the task's git_branch "
    "locally; never modify the branch — auditors report, they do not edit "
    "(Section 11.2).\n"
    "3. Run the matrix: execute the project's full test and lint commands "
    "and record real exit codes.\n"
    "4. Review the diff: compare the change against the acceptance "
    "criteria and target_scope from get_task_details.\n"
    "5. Submit the verdict: call submit_audit_verdict with verdict "
    "pass, flag_risk or fail, honest confidence 1-5, and evidence "
    "entries (label, command, exit_code) plus per-criterion results.\n"
    "\n"
    "The verdict is input, not the outcome: the backend's Policy Engine "
    "decides the task's final state (Section 9.4)."
)
