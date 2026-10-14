"""Merge Executor error types (parent plan Sections 10.8, 11.4; WP-3.7).

One executor-scoped exception, deliberately *not* an :class:`ApiError`:
everything here is a **local** condition (guard refusal, missing branch,
worktree creation/cleanup failure) that the Section 11.4 loop reports
through the T18 ``failed`` path with the message as ``details`` — never
a wire error code invented by the host (Section 20.4 item 5 keeps the
catalog backend-owned).
"""

from __future__ import annotations

__all__ = ["MergeExecutorError"]


class MergeExecutorError(Exception):
    """A guard refusal or local Git/workspace failure inside the executor.

    ``reason`` is the structural explanation (which allowlist rule, which
    missing precondition); the string form carries both so a T18 details
    field or a structured log line stays self-describing.
    """

    def __init__(self, message: str, *, reason: str = "") -> None:
        super().__init__(f"{message} ({reason})" if reason else message)
        self.message = message
        self.reason = reason
