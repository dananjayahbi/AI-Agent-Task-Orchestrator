"""``orchestrator:submit_for_audit`` prompt (parent plan Sections 10.7, 10.6
rules 3–4, 11.1 steps 6–7; FR-MCP-04; MT-2.8-03).

The coder's closing move — the three Section 10.7 behaviors in plan order
(run verification, summarize, submit). Honest-risk-flag wording follows
Section 11.1 step 6 so T8 self-flagging is never discouraged (MT-2.8-03 risk
note), and the outcome states stay the **backend's** decision (T7
``to_be_audited`` / T8 ``in_human_review`` via the Policy Engine — Section
9.4, ADR-009): this prompt promises no particular state. ``LEASE_EXPIRED`` /
``TASK_STATE_CONFLICT`` means stop and re-orient (Section 11.1 step 7), and
the workflow works without the prompt (NFR-08, ADR-011) — rules 3–4 and the
tool description carry the same steps.
"""

from __future__ import annotations

from typing import Final

__all__ = ["DESCRIPTION", "NAME", "TEXT"]

NAME: Final = "orchestrator:submit_for_audit"

DESCRIPTION: Final = "Run verification, summarize, submit (Section 10.7)."

TEXT: Final = (
    "Optional guidance for finishing coder work on a held task "
    "(Section 10.7). The same steps are rules 3, 4 and 8 of the rules "
    "block.\n"
    "\n"
    "1. Run verification: execute the task's test command and record the "
    "real exit codes — never report a pass you did not observe.\n"
    "2. Summarize: write a concise execution_summary of what was done, "
    "which tests ran and their exit codes.\n"
    "3. Submit: commit the work, then call submit_task_resolution with the "
    "task's assigned git_branch, the commit_sha, the summary, and an honest "
    "risk flag — set requires_human_attention (with risk_justification) "
    "whenever anything is uncertain, incomplete or risky.\n"
    "\n"
    "Outcome states are the backend's decision: the submission lands in "
    "to_be_audited or in_human_review per the Policy Engine — the tool "
    "reports which. If LEASE_EXPIRED or TASK_STATE_CONFLICT appears, stop "
    "and re-orient instead of resubmitting blindly."
)
