"""Local submission spool — durable retention across backend outages
(parent plan Sections 10.10, 18 (chaos row); NFR-04, ADR-012, NFR-12;
MT-2.6-05).

Section 10.10's resilience contract, made physical: *"in-flight submission
data (patch, summary) is held locally until acknowledged."* The moment
:mod:`orchestrator_bridge.tools.submit` assembles a payload it is written
here — **before** the network attempt — so an outage or a killed bridge can
delay an outcome but never destroy evidence (WP-2.6 acceptance; Section 18
chaos row).

Design contract:

* **persist-before-send** — :meth:`SubmissionSpool.hold` returns only after
  the entry is on disk (atomic write: temp file + ``os.replace``); the
  submit handler makes no HTTP call before that returns.
* **one key, forever** — each entry stores the ``Idempotency-Key`` minted
  for the submission; every retry (transport backoff inside one call, or
  the restart sweep below) replays that exact key with the stored body, so
  the backend replays instead of re-executing (ADR-012; a "fresh key per
  retry" bug would create duplicate resolutions — pinned by test).
* **ack clears** — only a backend-acknowledged submission is complete; the
  entry is deleted then (best-effort: a failed delete is harmless because a
  later replay with the same key replays).
* **restart recovery** — the entrypoints construct this spool and call
  :meth:`resume` once at startup; unacknowledged entries for the *bound
  project* are re-sent (entries for other projects are retained for their
  own sessions — a project's token never replays another project's work).
* **classification** — retryable failures keep the entry (the decision is
  still pending on the network); a definitive backend rejection deletes it
  (the payload can never succeed as-is; the agent must fix and resubmit —
  recorded rule, WP-2.6 changelog). Expiry is bounded
  (:data:`DEFAULT_MAX_AGE_DAYS`) with an operator-visible prune message.
* **hygiene** — files are created with ``0o600`` where the OS honors it,
  live outside any Git repository (the user config area), and the payload
  carries no tokens or absolute environment paths by construction
  (auth rides request headers, never the body). Logs name entry ids, task
  ids and error codes — never payload contents (Section 12.4).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .api_errors import ApiError
from .config import default_user_config_path
from .transport import ApiClient

__all__ = [
    "DEFAULT_MAX_AGE_DAYS",
    "ResumeReport",
    "SpoolEntry",
    "SubmissionSpool",
    "default_spool_dir",
]

_LOGGER = logging.getLogger("bridge.submission_spool")

#: Bounded retention for stuck entries (MT-2.6-05 spool hygiene): older
#: payloads never reached the backend and are pruned with an operator
#: message rather than accumulating forever.
DEFAULT_MAX_AGE_DAYS = 7

#: The subdirectory of the user orchestrator config area holding the spool
#: (outside every Git repository; ``%APPDATA%\\orchestrator\\submission-spool``
#: on Windows, ``~/.config/orchestrator/submission-spool`` on POSIX).
SPOOL_DIRNAME = "submission-spool"

#: Operator escape hatch: point the spool at a specific directory (tests,
#: multi-user hosts). Unset means the default user-area location.
SPOOL_DIR_ENV = "ORCHESTRATOR_SPOOL_DIR"


def default_spool_dir() -> Path:
    """The user-level spool directory (config area override honored)."""
    override = os.environ.get(SPOOL_DIR_ENV)
    if override and override.strip():
        return Path(override.strip())
    return default_user_config_path().parent / SPOOL_DIRNAME


@dataclass(frozen=True, slots=True)
class SpoolEntry:
    """One held submission: the exact bytes and key a retry must replay."""

    id: str
    project_id: str
    task_id: str
    path: str
    body: dict[str, Any]
    idempotency_key: str
    created_at: str
    attempts: int = 0
    last_error: str | None = None

    def as_file(self) -> dict[str, Any]:
        """The on-disk JSON document (stable key order)."""
        return {
            "attempts": self.attempts,
            "body": self.body,
            "created_at": self.created_at,
            "id": self.id,
            "idempotency_key": self.idempotency_key,
            "last_error": self.last_error,
            "path": self.path,
            "project_id": self.project_id,
            "task_id": self.task_id,
        }

    @classmethod
    def from_file(cls, document: Any) -> SpoolEntry:
        """Parse one on-disk document (raises ``ValueError`` when malformed)."""
        if not isinstance(document, dict):
            raise ValueError("spool entry is not an object")
        body = document.get("body")
        if not isinstance(body, dict):
            raise ValueError("spool entry body is not an object")
        values: dict[str, str] = {}
        for key in ("id", "project_id", "task_id", "path", "idempotency_key", "created_at"):
            value = document.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError(f"spool entry field {key!r} is missing")
            values[key] = value
        attempts = document.get("attempts")
        last_error = document.get("last_error")
        return cls(
            id=values["id"],
            project_id=values["project_id"],
            task_id=values["task_id"],
            path=values["path"],
            body=body,
            idempotency_key=values["idempotency_key"],
            created_at=values["created_at"],
            attempts=(
                attempts if isinstance(attempts, int) and not isinstance(attempts, bool) else 0
            ),
            last_error=last_error if isinstance(last_error, str) else None,
        )


@dataclass(frozen=True, slots=True)
class ResumeReport:
    """What one startup sweep did (logged, never raised)."""

    replayed: int  # acknowledged on this sweep
    retained: int  # still retryable — kept for the next sweep
    discarded: int  # definitively rejected by the backend — dropped
    foreign: int  # other projects' entries — kept for their own sessions

    def as_dict(self) -> dict[str, int]:
        return dataclasses.asdict(self)  # pragma: no cover - trivial view


@dataclass(slots=True)
class SubmissionSpool:
    """One directory of held submissions (user-level; one file per entry)."""

    directory: Path
    max_age_days: int = DEFAULT_MAX_AGE_DAYS
    now: Callable[[], datetime] = field(default=lambda: datetime.now(tz=UTC))

    @classmethod
    def default(cls) -> SubmissionSpool:
        """The user-level spool (see :func:`default_spool_dir`)."""
        return cls(directory=default_spool_dir())

    # --- write side (the submit handler's persist-before-send) ---------------

    def hold(
        self,
        *,
        project_id: str,
        task_id: str,
        path: str,
        body: dict[str, Any],
        idempotency_key: str,
    ) -> SpoolEntry:
        """Persist one assembled submission; returns the held entry.

        Raises :class:`OSError` when the payload cannot be made durable —
        the submit handler turns that into a structured non-retryable
        failure and makes **no** network attempt (persist or nothing).
        """
        entry = SpoolEntry(
            id=uuid.uuid4().hex,
            project_id=project_id,
            task_id=task_id,
            path=path,
            body=body,
            idempotency_key=idempotency_key,
            created_at=self.now().isoformat(),
        )
        self._write(entry)
        return entry

    def resolve(self, entry_id: str) -> None:
        """Acknowledge/drop one entry. Failure is logged, never raised.

        Called after a backend acknowledgment (complete) or a definitive
        rejection (can never succeed as-is). A failed delete is safe: the
        entry replays with its original key and the backend replays the
        stored outcome.
        """
        try:
            self._file(entry_id).unlink(missing_ok=True)
        except OSError as exc:
            _LOGGER.warning(
                "submission spool entry could not be cleared",
                extra={
                    "event": "spool_clear_failed",
                    "entry_id": entry_id,
                    "error": type(exc).__name__,
                },
            )

    def mark_failed(self, entry_id: str, *, error_code: str) -> None:
        """Record one exhausted retryable attempt (bookkeeping only)."""
        try:
            entry = self._read(self._file(entry_id))
        except (OSError, ValueError):
            return
        updated = dataclasses.replace(entry, attempts=entry.attempts + 1, last_error=error_code)
        try:
            self._write(updated)
        except OSError:
            pass  # the entry still exists un-refreshed; retention still applies

    # --- read side (the startup sweep) ----------------------------------------

    def entries(self) -> list[SpoolEntry]:
        """Held entries, oldest first — expired ones pruned on the way.

        A malformed file is skipped and logged (an operator can inspect it);
        it never crashes the sweep.
        """
        if not self.directory.is_dir():
            return []
        cutoff = self.now() - timedelta(days=self.max_age_days)
        kept: list[SpoolEntry] = []
        expired = 0
        for path in sorted(self.directory.glob("*.json")):
            try:
                entry = self._read(path)
            except (OSError, ValueError):
                _LOGGER.warning(
                    "submission spool entry is unreadable and was skipped",
                    extra={"event": "spool_entry_unreadable", "file": path.name},
                )
                continue
            try:
                created = datetime.fromisoformat(entry.created_at)
            except ValueError:
                created = cutoff  # unparseable age → treated as current
            if created < cutoff:
                expired += 1
                path.unlink(missing_ok=True)
                continue
            kept.append(entry)
        if expired:
            # The operator message: these payloads never reached the backend.
            _LOGGER.warning(
                f"discarded {expired} stuck submission spool entries older than "
                f"{self.max_age_days} days",
                extra={
                    "event": "spool_pruned",
                    "count": expired,
                    "max_age_days": self.max_age_days,
                },
            )
        return kept

    def resume(self, client: ApiClient, *, project_id: str) -> ResumeReport:
        """Re-send this project's unacknowledged submissions, oldest first.

        One sweep per startup: each entry is replayed with its **stored**
        body and **stored** idempotency key — the backend replays a
        previously-accepted submission instead of transitioning twice. An
        entry whose retryable failure persists stays for the next sweep; a
        definitive rejection is dropped. Never raises (startup must not die
        because of the spool).
        """
        replayed = retained = discarded = foreign = 0
        for entry in self.entries():
            if entry.project_id != project_id:
                foreign += 1
                continue
            try:
                client.request(
                    "POST", entry.path, body=entry.body, idempotency_key=entry.idempotency_key
                )
            except ApiError as exc:
                if exc.retryable:
                    self.mark_failed(entry.id, error_code=str(exc.code))
                    retained += 1
                    _LOGGER.info(
                        "spooled submission still unreachable",
                        extra={
                            "event": "spool_replay_retryable",
                            "entry_id": entry.id,
                            "task_id": entry.task_id,
                            "error_code": str(exc.code),
                        },
                    )
                else:
                    self.resolve(entry.id)
                    discarded += 1
                    _LOGGER.warning(
                        "spooled submission rejected on replay and was discarded",
                        extra={
                            "event": "spool_discarded",
                            "entry_id": entry.id,
                            "task_id": entry.task_id,
                            "error_code": str(exc.code),
                        },
                    )
            except Exception:
                retained += 1  # unexpected local failure: keep the evidence
                _LOGGER.warning(
                    "spooled submission replay failed unexpectedly",
                    extra={"event": "spool_replay_error", "entry_id": entry.id},
                )
            else:
                self.resolve(entry.id)
                replayed += 1
                _LOGGER.info(
                    "spooled submission acknowledged and cleared",
                    extra={
                        "event": "spool_replayed",
                        "entry_id": entry.id,
                        "task_id": entry.task_id,
                    },
                )
        return ResumeReport(
            replayed=replayed, retained=retained, discarded=discarded, foreign=foreign
        )

    # --- file plumbing (atomic, restrictive, never logged) --------------------

    def _file(self, entry_id: str) -> Path:
        return self.directory / f"{entry_id}.json"

    def _read(self, path: Path) -> SpoolEntry:
        return SpoolEntry.from_file(json.loads(path.read_text(encoding="utf-8")))

    def _write(self, entry: SpoolEntry) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._file(entry.id)
        temporary = self.directory / f"{entry.id}.json.tmp"
        payload = json.dumps(entry.as_file(), sort_keys=True, ensure_ascii=True)
        # 0o600 where the OS honors it (POSIX); Windows inherits the profile
        # ACLs — the best-effort chmod below keeps the intent explicit.
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        try:
            os.chmod(temporary, 0o600)
        except OSError:  # pragma: no cover - platform-dependent best effort
            pass
        os.replace(temporary, target)
