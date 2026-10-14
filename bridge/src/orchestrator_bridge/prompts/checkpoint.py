"""``orchestrator:checkpoint`` prompt (parent plan Sections 10.7, 8.6, 10.6
rule 5; FR-MCP-04; MT-2.8-02).

The lease-keeping prompt (RISK-02 mitigation): commit current work, then log
a checkpoint — the exact two Section 10.7 behaviors in that order. Wording
matches the channels that carry the same discipline without the prompt
(NFR-08, ADR-011): rule 5 of the rules block and the ``log_task_checkpoint``
tool description. Lease semantics are restated **by pointer, never invented**
— the backend owns the extension formula and the hard cap (Section 8.6;
WP-1.8), the tool returns the ``next_checkpoint_due`` hint (WP-2.6), and a
late checkpoint answers ``LEASE_EXPIRED``: stop and re-orient, never
resurrect a lost lease (Section 11.1 step 7).
"""

from __future__ import annotations

from typing import Final

__all__ = ["DESCRIPTION", "NAME", "TEXT"]

NAME: Final = "orchestrator:checkpoint"

DESCRIPTION: Final = "Commit current work and log a checkpoint (Section 10.7)."

TEXT: Final = (
    "Optional guidance for reporting progress on a held task "
    "(Section 10.7). The same discipline is rule 5 of the rules block and "
    "the log_task_checkpoint description.\n"
    "\n"
    "1. Commit current work first: a checkpoint reports committed progress, "
    "so commit before logging.\n"
    "2. Log the checkpoint: call log_task_checkpoint with an honest message "
    "and an optional percentage. The response returns the new lease expiry "
    "and a next_checkpoint_due hint — send the next checkpoint before that "
    "instant.\n"
    "\n"
    "Lease rules (Section 8.6): a checkpoint extends the lease only while "
    "you still own it, and never beyond the lease hard cap — after the cap "
    "the tool's next_action says submit or release. A LEASE_EXPIRED answer "
    "means the lease is gone: stop and re-orient with get_available_tasks; "
    "never attempt to resurrect a lost lease."
)
