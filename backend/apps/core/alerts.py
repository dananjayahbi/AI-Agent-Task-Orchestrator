"""Section 17 alert rules — MT-6.4-02 (NFR-10, RISK-12; WP-6.4).

Exactly the six alerts of the plan's Section 17 **Alerts** row, none renamed,
added or dropped: sweeper not running, backlog of unprocessed attachments,
push failures, tunnel down, repeated auth failures, disk usage on media
volume. Each rule pairs a signal MT-6.4-01 landed (metrics counters,
heartbeats) or a cheap DB/cache read with a threshold whose rationale and
plan anchor are tabulated in ``docs/plan/alerts.md`` (the rules catalog).

**Evaluation is pull-based** (recorded channel decision, no hidden one):
:func:`evaluate_alerts` runs whenever someone reads alert state — the
ops-overview endpoint (MT-6.4-03) or a test — and a structured WARNING log
line is emitted on each ok→firing transition. There is no scheduled emitter
and no external paging (out of scope per the MT); the Section 9.9 stalled
detector keeps owning ``system.alert`` Event rows — alert evaluation never
writes Events (a read path must not mutate the audit trail).

**Firing "since"** is tracked in the cache (``alerts:firing_since:{id}``):
set on the first evaluation that observes firing, cleared when the rule goes
back to ok. Under a cache restart the since-stamp resets — honest, and
documented like the other LocMem/Redis seams.

**No secrets** (Section 12.4): payloads carry metric names, counts, ages and
thresholds only — never a token, task id, attachment content, or even a raw
client IP (auth-failure sources are hashed before they touch a cache key and
only counts reach the payload).

Tunnel honesty (Section 15.4; the MT's risk note): the tunnel is
outbound-only by design, so the backend cannot probe it. The rule reads the
last status an operator/monitoring host reported through
:func:`record_tunnel_status` (the documented ``report_tunnel_status``
management command runs the same check the Compose healthcheck runs). Until
a first report exists the rule stays ``unknown`` — not firing, not pretending
the tunnel is up; the limitation is recorded in the rules catalog rather
than papered over.
"""

from __future__ import annotations

import hashlib
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

_PREFIX: Final = "alerts"

#: Section 17's six alert names, in plan order — the catalog contract.
#: ``evaluate_alerts`` returns exactly these ids; a drift fails the tests.
ALERT_IDS: Final[tuple[str, ...]] = (
    "sweeper_not_running",
    "attachment_backlog",
    "push_failures",
    "tunnel_down",
    "repeated_auth_failures",
    "media_disk_usage",
)

_TUNNEL_STATUS_KEY: Final = f"{_PREFIX}:tunnel:status"
_AUTH_BUCKET_KEY: Final = f"{_PREFIX}:authfail:bucket"


# --- recording seams (called where the events happen) -----------------------


def record_auth_failure(source: str) -> None:
    """Count one failed owner-login attempt from *source* (an IP or identity
    string) into the current fixed window.

    The source is hashed before it reaches a cache key and never reaches an
    alert payload (Section 12.4) — the alert reports counts, not who failed.
    One read-modify-write dict per window bucket, the same M1 pattern as
    ``metrics.record_api_latency``'s per-route table; a hot multi-worker
    deployment would want a sharded counter (documented limitation).
    """
    window = settings.ALERT_AUTH_FAILURE_WINDOW_SECONDS
    bucket = int(time.time() // window) * window
    key = f"{_AUTH_BUCKET_KEY}:{bucket}"
    table: dict[str, int] = cache.get(key) or {}
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    table[digest] = table.get(digest, 0) + 1
    # TTL past the window so a late read of the just-closed bucket still works.
    cache.set(key, table, window * 2)


def record_tunnel_status(up: bool) -> None:
    """Stamp the host-side tunnel status (Section 16.1 cloudflared health).

    Reporter: the ``report_tunnel_status`` management command (or any
    monitoring host) after running the same check the Compose healthcheck
    runs (``cloudflared tunnel ready``). ``up=False`` fires MT-6.4-02's
    tunnel alert; a report older than ``ALERT_TUNNEL_MAX_STATUS_AGE_SECONDS``
    fires it too (the reporter went silent — cannot confirm the tunnel).
    """
    cache.set(
        _TUNNEL_STATUS_KEY,
        {"up": bool(up), "at": timezone.now().isoformat()},
        timeout=None,  # the age check below does the staleness work
    )


# --- per-rule evaluation ----------------------------------------------------


@dataclass(frozen=True)
class AlertState:
    """One rule's current state — the payload MT-6.4-03's view renders."""

    id: str
    name: str
    severity: str  # "critical" | "warning"
    firing: bool
    status: str  # "firing" | "ok" | "unknown" (signal never reported)
    since: str | None  # ISO when firing first observed (else None)
    signal: dict[str, Any]  # numbers only — never identities or secrets
    threshold: dict[str, Any]
    runbook: str | None  # Section 17 runbook name where one exists

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready view of the state (field names are the contract)."""
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity,
            "firing": self.firing,
            "status": self.status,
            "since": self.since,
            "signal": self.signal,
            "threshold": self.threshold,
            "runbook": self.runbook,
        }


def _age_seconds(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    try:
        return round((now - datetime.fromisoformat(iso)).total_seconds(), 3)
    except ValueError:
        return None


def _sweeper(now: datetime) -> AlertState:
    """Section 9.9: the lease sweeper runs every 60 s; RISK-12's mitigation.

    Firing when the heartbeat is missing (the sweeper has never run in this
    counter store's lifetime — true on a cold stack until the first sweep,
    which the beat schedules within one cadence) or older than the threshold
    (3× the 60 s cadence by default — margin over one missed beat).
    """
    from apps.core.metrics import heartbeat_age_seconds

    age = heartbeat_age_seconds("sweeper", now)
    threshold = settings.ALERT_SWEEPER_MAX_HEARTBEAT_SECONDS
    firing = age is None or age > threshold
    # Onset is tracked by _track_since (the heartbeat age alone cannot date
    # the transition); since=None hands that job over.
    return AlertState(
        id="sweeper_not_running",
        name="Sweeper not running",
        severity="critical",
        firing=firing,
        status="firing" if firing else "ok",
        since=None,
        signal={"heartbeat_age_seconds": age},
        threshold={"max_heartbeat_age_seconds": threshold},
        runbook=None,  # Section 17 lists no sweeper-down runbook
    )


def _attachment_backlog(now: datetime) -> AlertState:
    """Backlog of unprocessed attachments: depth *or* oldest-item age.

    Non-terminal means ``uploaded``/``processing`` and not soft-deleted.
    Age fires past the retry envelope's outer bound (the pipeline's
    documented backoff is 60 s × 2^attempt over
    ``ATTACHMENT_RETRY_MAX_ATTEMPTS`` ≈ 3 min of retries — 15 min leaves
    margin); depth is a configurable default flagged for owner confirmation.
    """
    from apps.attachments.models import ProcessingStatus, TaskAttachment

    pending = TaskAttachment.objects.filter(
        processing_status__in=(ProcessingStatus.UPLOADED, ProcessingStatus.PROCESSING),
        deleted_at__isnull=True,
    )
    depth = pending.count()
    oldest = pending.order_by("created_at").values_list("created_at", flat=True).first()
    oldest_age = round((now - oldest).total_seconds(), 3) if oldest else None
    max_age = settings.ALERT_ATTACHMENT_BACKLOG_MAX_AGE_SECONDS
    max_depth = settings.ALERT_ATTACHMENT_BACKLOG_MAX_DEPTH
    firing = (oldest_age is not None and oldest_age > max_age) or depth > max_depth
    return AlertState(
        id="attachment_backlog",
        name="Backlog of unprocessed attachments",
        severity="warning",
        firing=firing,
        status="firing" if firing else "ok",
        since=oldest.isoformat() if oldest and firing else None,
        signal={"depth": depth, "oldest_age_seconds": oldest_age},
        threshold={"max_age_seconds": max_age, "max_depth": max_depth},
        runbook=None,
    )


def _push_failures() -> AlertState:
    """Push failures: success rate under the floor, past a minimum sample.

    Reads MT-6.4-01's push counters. Zero dispatches → ok with a ``null``
    rate (no dispatcher has landed yet — honest, not a lie; WP-5.4 wires
    ``record_push_outcome``). NFR-03's 10 s dispatch window is the related
    contract cited in the catalog.
    """
    from apps.core.metrics import push_counts

    dispatched, succeeded = push_counts()
    rate = round(succeeded / dispatched, 4) if dispatched else None
    min_rate = settings.ALERT_PUSH_MIN_SUCCESS_RATE_PERCENT / 100.0
    min_dispatches = settings.ALERT_PUSH_MIN_DISPATCHES
    firing = dispatched >= min_dispatches and (rate is not None and rate < min_rate)
    return AlertState(
        id="push_failures",
        name="Push failures",
        severity="warning",
        firing=firing,
        status="firing" if firing else "ok",
        since=None,
        signal={"dispatched": dispatched, "succeeded": succeeded, "success_rate": rate},
        threshold={
            "min_success_rate": min_rate,
            "min_dispatches": min_dispatches,
        },
        runbook=None,
    )


def _tunnel_down(now: datetime) -> AlertState:
    """Tunnel down — host-side detection only (Sections 15.1, 15.4, 16.1).

    The backend cannot probe the outbound-only tunnel; it reads the last
    reported status. ``unknown`` (never reported) does not fire — the
    limitation is documented rather than faked. Section 15.4's failure mode
    (LAN and agents continue) makes this a warning, not a page.
    """
    report: dict[str, Any] | None = cache.get(_TUNNEL_STATUS_KEY)
    max_age = settings.ALERT_TUNNEL_MAX_STALE_SECONDS
    if not report:
        return AlertState(
            id="tunnel_down",
            name="Tunnel down",
            severity="warning",
            firing=False,
            status="unknown",
            since=None,
            signal={"reported_up": None, "status_age_seconds": None},
            threshold={"max_status_age_seconds": max_age},
            runbook="tunnel down",
        )
    age = _age_seconds(report.get("at"), now)
    up = bool(report.get("up"))
    firing = (not up) or (age is not None and age > max_age)
    since = report.get("at") if firing else None
    return AlertState(
        id="tunnel_down",
        name="Tunnel down",
        severity="warning",
        firing=firing,
        status="firing" if firing else "ok",
        since=since,
        signal={"reported_up": up, "status_age_seconds": age},
        threshold={"max_status_age_seconds": max_age},
        runbook="tunnel down",
    )


def _repeated_auth_failures(now: datetime) -> AlertState:
    """Repeated auth failures — Section 15.3 layer-4 anomaly signal.

    Counts are per hashed source within one fixed window bucket (the same
    windowing model as ``claims_per_minute``); the payload reports only the
    worst count and how many sources crossed the floor — never who (12.4).
    The instrumented surface is the owner-login failure path; token-auth
    failure counting is a recorded follow-up (rules catalog).
    """
    window = settings.ALERT_AUTH_FAILURE_WINDOW_SECONDS
    bucket = int(now.timestamp() // window) * window
    table: dict[str, int] = cache.get(f"{_AUTH_BUCKET_KEY}:{bucket}") or {}
    threshold_count = settings.ALERT_AUTH_FAILURES_MAX_PER_WINDOW
    offenders = {k: v for k, v in table.items() if v >= threshold_count}
    firing = bool(offenders)
    since = datetime.fromtimestamp(bucket, tz=UTC).isoformat() if firing else None
    return AlertState(
        id="repeated_auth_failures",
        name="Repeated auth failures",
        severity="warning",
        firing=firing,
        status="firing" if firing else "ok",
        since=since,
        signal={
            "worst_source_failures": max(table.values(), default=0),
            "sources_over_threshold": len(offenders),
            "window_seconds": window,
        },
        threshold={"max_failures_per_source": threshold_count},
        runbook=None,
    )


def _media_disk_usage() -> AlertState:
    """Disk usage on the Section 16.1/16.3 media volume.

    Measured at evaluation time on ``MEDIA_ROOT``'s filesystem. An
    unreachable media root (mount gone) yields ``unknown`` — cannot measure,
    will not pretend. The backup destination's second-location disk
    (Section 16.5) is outside this process's reach; recorded as a limitation
    in the rules catalog.
    """
    try:
        usage = shutil.disk_usage(settings.MEDIA_ROOT)
    except OSError:
        return AlertState(
            id="media_disk_usage",
            name="Disk usage on media volume",
            severity="critical",
            firing=False,
            status="unknown",
            since=None,
            signal={"used_percent": None},
            threshold={"max_used_percent": settings.ALERT_DISK_USAGE_MAX_PERCENT},
            runbook=None,
        )
    percent = round(usage.used / usage.total * 100, 2) if usage.total else 0.0
    max_percent = settings.ALERT_DISK_USAGE_MAX_PERCENT
    firing = percent >= max_percent
    return AlertState(
        id="media_disk_usage",
        name="Disk usage on media volume",
        severity="critical",
        firing=firing,
        status="firing" if firing else "ok",
        since=None,
        signal={"used_percent": percent},
        threshold={"max_used_percent": max_percent},
        runbook=None,
    )


# --- since-tracking + orchestration -----------------------------------------


def _since_key(alert_id: str) -> str:
    return f"{_PREFIX}:firing_since:{alert_id}"


def _track_since(state: AlertState, *, observed_firing: bool) -> AlertState:
    """Stamp/clear the firing-since cache; return the state with ``since``.

    ``since`` is the first evaluation timestamp that observed this alert
    firing (pull-based evaluation cannot know an earlier onset — documented
    in the rules catalog). Rules that carry their own onset signal (the
    heartbeat age, the oldest backlog item, the tunnel report) keep it.
    """
    if state.since is not None:
        return state  # onset derivable from the signal itself
    if observed_firing:
        key = _since_key(state.id)
        stamp: str | None = cache.get(key)
        if stamp is None:
            stamp = timezone.now().isoformat()
            cache.set(key, stamp, None)
        since = stamp
    else:
        key = _since_key(state.id)
        cache.delete(key)
        since = None
    return AlertState(
        id=state.id,
        name=state.name,
        severity=state.severity,
        firing=state.firing,
        status=state.status,
        since=since,
        signal=state.signal,
        threshold=state.threshold,
        runbook=state.runbook,
    )


def evaluate_alerts(now: datetime | None = None) -> list[dict[str, Any]]:
    """Evaluate all six Section 17 rules; return their states in plan order.

    Pure read path: no Event rows, no external calls. A WARNING is logged on
    each ok→firing transition (the recorded secondary surfacing channel) so
    a state change is visible in structured logs even when nobody loads the
    dashboard.
    """
    import logging

    now = now or timezone.now()
    states = (
        _sweeper(now),
        _attachment_backlog(now),
        _push_failures(),
        _tunnel_down(now),
        _repeated_auth_failures(now),
        _media_disk_usage(),
    )
    logger = logging.getLogger(__name__)
    tracked: list[dict[str, Any]] = []
    for state in states:
        previous_firing = bool(cache.get(_since_key(state.id)))
        final = _track_since(state, observed_firing=state.firing)
        if final.firing and not previous_firing:
            logger.warning(
                "alert firing: %s (%s) signal=%s threshold=%s",
                final.id,
                final.severity,
                final.signal,
                final.threshold,
            )
        tracked.append(final.as_dict())
    return tracked
