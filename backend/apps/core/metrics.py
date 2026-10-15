"""Section 17 observability: the ``/metrics`` JSON endpoint (NFR-10; WP-6.4).

**Format choice — JSON, not Prometheus text exposition.** Recorded in
``docs/plan/metrics.md``: the M1 consumer is an internal/LAN scrape and human
debugging, JSON needs no new runtime dependency (no ``prometheus_client``), and
Django's cache API is the counter store (Redis in prod, LocMem in the unit
layer). ``collect()`` merges those cache counters with two DB gauges (active
leases, per-state cycle time) and the SSE hub's process-local connection count.

**Instrumentation seams** — counters are written where the events already
happen: the claim path (``leases.claim.claim_task``), the lease sweeper
(``leases.sweeper``), the attachment pipeline (``attachments.pipeline``), and
the request-timing middleware (``core.middleware``). ``record_push_outcome`` is
the Section 17 push-dispatch seam WP-5.4 will call once a real push dispatcher
exists; it reads ``0 dispatched`` until then (the device leg is out of M1 scope).

**No secrets** — every label is a metric name, a resolved route pattern, a
state name or an HTTP method/status. Never a token, a task id, or attachment
content (Section 17's no-secrets rule; the middleware normalises the path to the
URL resolver's route pattern so dynamic segments do not leak or explode
cardinality).

The route is a **plain Django view** (not a DRF ``APIView``) so it stays out of
the OpenAPI document and therefore out of the schema-diff gate; it is
internal/LAN-only like Health (not on the tunnel allowlist).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpRequest, JsonResponse
from django.utils import timezone

_PREFIX = "metrics"
# Cumulative counters never expire; the minute-bucketed claims key is re-keyed
# every minute and only needs to outlive a couple of windows.
_FOREVER: int | None = None
_BUCKET_TTL_S = 120


# --- counter store (Django cache API) ---------------------------------------


def _incr(key: str, amount: int = 1, *, ttl: int | None = None) -> int:
    """Increment a cache counter, seeding it at 0 on first touch.

    ``cache.add`` is the atomic seed; ``incr`` then bumps. ``ttl=None`` keeps a
    cumulative counter forever, a finite ttl bounds a re-keyed bucket.
    """
    cache.add(key, 0, timeout=ttl)
    return int(cache.incr(key, amount))


def _get(key: str, default: int = 0) -> int:
    try:
        return int(cache.get(key, default))
    except (TypeError, ValueError):
        return default


def _minute_bucket() -> str:
    return timezone.now().strftime("%Y%m%d%H%M")


# --- instrumentation seams ---------------------------------------------------


def record_claim() -> None:
    """One successful claim (Section 9.3) — feeds ``claims_per_minute``."""
    _incr(f"{_PREFIX}:claims:{_minute_bucket()}", ttl=_BUCKET_TTL_S)


def record_claim_conflict() -> None:
    """A lost claim race: ``TASK_ALREADY_CLAIMED``/``CONCURRENCY_LIMIT_REACHED``."""
    _incr(f"{_PREFIX}:claim_conflicts", ttl=_FOREVER)


def record_lease_expirations(count: int) -> None:
    """Leases the sweeper reclaimed/escalated/released in one pass (T5)."""
    if count:
        _incr(f"{_PREFIX}:lease_expirations", count, ttl=_FOREVER)


def record_pipeline(outcome: str, duration_ms: float) -> None:
    """One attachment pipeline run: per-outcome count + duration sum/count."""
    _incr(f"{_PREFIX}:pipeline:count:{outcome}", ttl=_FOREVER)
    _incr(f"{_PREFIX}:pipeline:duration_ms_sum", int(duration_ms), ttl=_FOREVER)
    _incr(f"{_PREFIX}:pipeline:duration_count", ttl=_FOREVER)


def record_push_outcome(success: bool) -> None:
    """A backend-observed push dispatch outcome (Section 17).

    The device leg is WP-5.4/WP-5.10's domain; until a real dispatcher calls
    this the counters stay at ``0 dispatched`` (documented, not a bug).
    """
    _incr(f"{_PREFIX}:push:dispatched", ttl=_FOREVER)
    if success:
        _incr(f"{_PREFIX}:push:succeeded", ttl=_FOREVER)


def record_api_latency(method: str, route: str, status: int, duration_ms: float) -> None:
    """One HTTP response: overall + per-(method, route, status) latency.

    ``route`` is the URL resolver's pattern (e.g. ``api/v1/tasks/<id>/claim``),
    never the raw path — no task ids leak and cardinality stays bounded. The
    per-route breakdown is a read-modify-write on one cache key; that is safe
    for the M1 scaffold's single-process/unit usage and is documented as a
    limitation in docs/plan/metrics.md (a hot multi-worker path would want a
    sharded counter). The overall ``api:count``/``api:duration_ms_sum`` stay
    atomic via ``incr``.
    """
    _incr(f"{_PREFIX}:api:count", ttl=_FOREVER)
    _incr(f"{_PREFIX}:api:duration_ms_sum", int(duration_ms), ttl=_FOREVER)
    key = f"{_PREFIX}:api:routes"
    table: dict[str, list[int]] = cache.get(key) or {}
    bucket = f"{method}:{route}:{status}"
    count, total = table.get(bucket, [0, 0])
    table[bucket] = [count + 1, total + int(duration_ms)]
    cache.set(key, table, None)


def _api_latency_by_route() -> dict[str, dict[str, float]]:
    table: dict[str, list[int]] = cache.get(f"{_PREFIX}:api:routes") or {}
    out: dict[str, dict[str, float]] = {}
    for bucket, (count, total) in table.items():
        method, route, status = bucket.split(":", 2)
        out[f"{method} {route} {status}"] = {
            "count": count,
            "duration_ms_avg": round(total / count, 3) if count else 0.0,
        }
    return out


def record_heartbeat(kind: str) -> None:
    """Worker/beat liveness stamp (ISO timestamp) — MT-6.4-02 alert input."""
    cache.set(f"{_PREFIX}:heartbeat:{kind}", timezone.now().isoformat(), None)


def heartbeat_age_seconds(kind: str, now: datetime | None = None) -> float | None:
    """Age of one heartbeat stamp (``worker``/``beat``/``sweeper``), or None
    if never stamped — the MT-6.4-02 sweeper alert's public signal reader."""
    now = now or timezone.now()
    raw = cache.get(f"{_PREFIX}:heartbeat:{kind}")
    return _heartbeat_age_seconds(raw, now)


def push_counts() -> tuple[int, int]:
    """``(dispatched, succeeded)`` — the MT-6.4-02 push-failure alert's
    public signal reader over the same counters the metric exposes."""
    return _get(f"{_PREFIX}:push:dispatched"), _get(f"{_PREFIX}:push:succeeded")


# --- DB gauges (computed at scrape) ------------------------------------------


def _active_leases(now: datetime) -> int:
    from apps.tasks.models import Task, TaskState

    live = (TaskState.IN_PROGRESS, TaskState.TO_BE_AUDITED)
    return Task.objects.filter(state__in=live, lease_expires_at__gt=now).count()


def _cycle_time_per_state(now: datetime) -> dict[str, float]:
    """Average seconds spent in each departed state, from TaskTransition history.

    A transition ``from_state -> to_state @ t`` closes the dwell in
    ``from_state`` that opened at the prior transition of the same task. The
    first transition of a task has no opener and is skipped. Windowed to the
    last 7 days to bound the scrape.
    """
    from apps.tasks.models import TaskTransition

    horizon = now - timedelta(days=7)
    rows = list(
        TaskTransition.objects.filter(timestamp__gte=horizon)
        .order_by("task_id", "timestamp")
        .values_list("task_id", "from_state", "to_state", "timestamp")
    )
    durs: dict[str, list[float]] = defaultdict(list)
    prev_task = prev_state = None
    prev_ts = None
    for task_id, _from_state, to_state, ts in rows:
        if prev_task == task_id and prev_state is not None and prev_ts is not None:
            # prev_state is the state entered at the prior transition; the gap
            # to this transition is the dwell spent in it.
            durs[prev_state].append((ts - prev_ts).total_seconds())
        prev_task, prev_state, prev_ts = task_id, to_state, ts
    return {state: round(sum(v) / len(v), 3) for state, v in durs.items()}


def _sse_connections() -> int:
    from apps.events.fanout import hub

    return hub.connection_count


def _heartbeat_age_seconds(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    try:
        return round((now - datetime.fromisoformat(iso)).total_seconds(), 3)
    except ValueError:
        return None


# --- collector ---------------------------------------------------------------


def collect() -> dict[str, Any]:
    """Assemble the nine Section 17 metrics into one JSON-ready document."""
    now = timezone.now()

    dispatched = _get(f"{_PREFIX}:push:dispatched")
    succeeded = _get(f"{_PREFIX}:push:succeeded")
    push_rate = round(succeeded / dispatched, 4) if dispatched else None

    pipe_count = _get(f"{_PREFIX}:pipeline:duration_count")
    pipe_sum = _get(f"{_PREFIX}:pipeline:duration_ms_sum")
    api_count = _get(f"{_PREFIX}:api:count")
    api_sum = _get(f"{_PREFIX}:api:duration_ms_sum")

    hb = {k: cache.get(f"{_PREFIX}:heartbeat:{k}") for k in ("worker", "beat", "sweeper")}

    return {
        "schema_version": "metrics-1",
        "generated_at": now.isoformat(),
        "metrics": {
            "claims_per_minute": _get(f"{_PREFIX}:claims:{_minute_bucket()}"),
            "claim_conflicts": _get(f"{_PREFIX}:claim_conflicts"),
            "active_leases": _active_leases(now),
            "lease_expirations": _get(f"{_PREFIX}:lease_expirations"),
            "task_cycle_time_per_state": _cycle_time_per_state(now),
            "attachment_pipeline": {
                "count_by_outcome": {
                    o: _get(f"{_PREFIX}:pipeline:count:{o}")
                    for o in ("ready", "skipped", "failed", "gone")
                },
                "duration_ms_avg": round(pipe_sum / pipe_count, 3) if pipe_count else None,
            },
            "sse_connections": _sse_connections(),
            "push_success_rate": push_rate,
            "api_latency": {
                "count": api_count,
                "duration_ms_avg": round(api_sum / api_count, 3) if api_count else None,
                "by_route": _api_latency_by_route(),
            },
            "heartbeats": {
                k: {"last_seen": v, "age_seconds": _heartbeat_age_seconds(v, now)}
                for k, v in hb.items()
            },
        },
    }


def metrics_view(request: HttpRequest) -> JsonResponse:
    """``GET /metrics`` — plain Django view, out of the OpenAPI document."""
    if not settings.METRICS_ENABLED:
        raise Http404("metrics endpoint disabled")
    return JsonResponse(collect())
