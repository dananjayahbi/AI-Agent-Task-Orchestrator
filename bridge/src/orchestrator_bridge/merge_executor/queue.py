"""Typed client for Section 9.2's three merge endpoints (MT-3.7-02; queue API from MT-3.7-01).

One declarative surface for the loop: poll ``GET /merge/pending``, claim
one entry with ``POST /merge/{task}/start``, report the outcome with
``POST /merge/{task}/result``. Paths resolve through the ``endpoints``
catalog (never re-typed literals — MT-2.3-05's single source of truth),
every mutation carries an explicit ADR-012 idempotency key minted **once
per logical operation** (a start retried across a backend outage replays
instead of double-claiming; a result report replays instead of applying a
second transition — Section 9.2's contract), and the result values are
exactly Section 7.2's reported flavors (``succeeded``/``conflict``/
``failed`` — never inferred, never renamed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import quote

from ..endpoints import endpoint
from ..idempotency import new_key
from ..transport import ApiClient

__all__ = [
    "RESULT_CONFLICT",
    "RESULT_FAILED",
    "RESULT_SUCCEEDED",
    "RESULT_VALUES",
    "MergeQueueClient",
    "MergeStart",
    "QueueItem",
    "QueuePage",
]

#: Section 11.4 step 4 / Section 7.2: the executor's reported outcomes.
RESULT_SUCCEEDED: Final = "succeeded"
RESULT_CONFLICT: Final = "conflict"
RESULT_FAILED: Final = "failed"
RESULT_VALUES: Final[frozenset[str]] = frozenset({RESULT_SUCCEEDED, RESULT_CONFLICT, RESULT_FAILED})


@dataclass(frozen=True, slots=True)
class QueueItem:
    """One ``GET /merge/pending`` row (Section 9.2; the executor's work unit).

    ``merge_strategy`` is the project policy's Section 7.2 value riding
    the queue row (never executor-side configuration); entries missing
    the field fall back to the plan's default ``squash``.
    """

    id: str
    project_id: str
    title: str
    state: str
    version: int
    merge_status: str
    branch_name: str | None
    merge_strategy: str = "squash"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> QueueItem:
        """Build from one wire row (the envelope's ``results`` members)."""
        return cls(
            id=str(payload["id"]),
            project_id=str(payload["project_id"]),
            title=str(payload["title"]),
            state=str(payload["state"]),
            version=int(payload["version"]),
            merge_status=str(payload["merge_status"]),
            branch_name=(
                str(payload["branch_name"]) if payload.get("branch_name") is not None else None
            ),
            merge_strategy=str(payload.get("merge_strategy") or "squash"),
        )


@dataclass(frozen=True, slots=True)
class QueuePage:
    """One queue page: the entries plus the opaque ``next_cursor`` (None = end)."""

    items: tuple[QueueItem, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class MergeStart:
    """One claim's post-transition identity (the result report chains on it)."""

    task_id: str
    version: int
    merge_status: str


class MergeQueueClient:
    """The Section 11.4 loop's backend surface over :class:`ApiClient`.

    ``api`` is the shared transport (its own retry/backoff, correlation
    scope and catalog error mapping). This client adds the merge
    workflow's shape on top — never a second retry layer, never a raw
    path literal.
    """

    def __init__(self, api: ApiClient) -> None:
        self._api = api

    def pending(self, *, page_size: int = 100, cursor: str | None = None) -> QueuePage:
        """One FIFO page of merge-pending tasks (Section 11.4 step 1)."""
        path = endpoint("merge_pending").path
        query = f"?page_size={page_size}"
        if cursor:
            query += f"&cursor={quote(cursor, safe='')}"
        payload = self._api.request("GET", f"{path}{query}")
        assert isinstance(payload, dict), "GET /merge/pending returned a non-object body"
        rows = payload.get("results")
        assert isinstance(rows, list), "the queue envelope lost its 'results' list"
        next_cursor = payload.get("next_cursor")
        return QueuePage(
            items=tuple(QueueItem.from_payload(dict(row)) for row in rows),
            next_cursor=str(next_cursor) if next_cursor is not None else None,
        )

    def start(self, item: QueueItem, *, idempotency_key: str | None = None) -> MergeStart:
        """Claim one queue entry (``pending`` → ``merging``; Section 11.4 step 2).

        The ADR-012 key is minted per (task, claim) — a transport retry
        or a loop-level retry after an outage replays the original claim
        instead of double-starting (Section 9.2's idempotency contract).
        The loop passes its own key so every loop-level retry reuses the
        exact same header.
        """
        path = endpoint("merge_start").path.format(task=item.id)
        payload = self._api.request(
            "POST",
            path,
            body={"version": item.version},
            idempotency_key=idempotency_key or new_key("merge-start", target=item.id),
        )
        assert isinstance(payload, dict), "POST /merge/start returned a non-object body"
        task = payload.get("task")
        assert isinstance(task, dict), "the start response lost its 'task' identity"
        return MergeStart(
            task_id=str(task["id"]),
            version=int(task["version"]),
            merge_status=str(task["merge_status"]),
        )

    def report(
        self,
        item: QueueItem,
        *,
        result: str,
        sha: str | None = None,
        details: str = "",
        version: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Report one merge outcome (Section 11.4 step 4; ``sha`` on success).

        The key is minted per (task, report) so an outage-interrupted
        report is retried without ever applying a second transition
        (ADR-012; MT-3.7-01's exactly-once contract). ``version`` is the
        CAS the start returned — a stale value answers VERSION_CONFLICT
        and applies nothing. The loop passes its own key so every
        loop-level retry reuses the exact same header.
        """
        if result not in RESULT_VALUES:
            raise ValueError(
                f"result must be one of {sorted(RESULT_VALUES)} (Section 7.2 values); "
                f"got {result!r}"
            )
        if result == RESULT_SUCCEEDED and not sha:
            raise ValueError("a 'succeeded' report requires the resulting sha (T17 guard)")
        path = endpoint("merge_result").path.format(task=item.id)
        body: dict[str, Any] = {"result": result, "details": details}
        if sha:
            body["sha"] = sha
        if version is not None:
            body["version"] = version
        payload = self._api.request(
            "POST",
            path,
            body=body,
            idempotency_key=idempotency_key or new_key("merge-result", target=item.id),
        )
        assert isinstance(payload, dict), "POST /merge/result returned a non-object body"
        return payload

    def project(self, project_id: str) -> dict[str, Any]:
        """``GET /projects/{pid}`` — the repo identity and default branch.

        The executor reads ``repo_path`` from this payload and checks it
        against the Section 10.2 allowlist **before** opening anything.
        """
        path = endpoint("project_context").path.format(pid=project_id)
        payload = self._api.request("GET", path)
        assert isinstance(payload, dict), "GET /projects/{pid} returned a non-object body"
        return payload

    def task(self, task_id: str) -> dict[str, Any]:
        """``GET /tasks/{id}`` — live queue state for MT-3.7-06 reconciliation.

        The catalogued read recovery uses to cross-check a journal entry
        (is the task *still* ``merging``?) before deciding one terminal
        outcome — never a second apply (ADR-012), never a fabricated
        report. The payload is the standard task body (Section 7.3
        identity plus ``merge_status``/``version``), so a ``QueueItem``
        reconstructs from it directly.
        """
        path = endpoint("task_details").path.format(id=task_id)
        payload = self._api.request("GET", path)
        assert isinstance(payload, dict), "GET /tasks/{id} returned a non-object body"
        return payload
