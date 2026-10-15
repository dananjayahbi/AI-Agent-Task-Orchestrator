'use client';

import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import type { AlertState, OpsHealth, OpsOverview } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { layout } from '@/lib/layout/styles';
import { useOpsOverviewQuery } from '@/lib/queries/ops';

/**
 * Operations view (MT-6.4-03; Section 17 Dashboards row; NFR-10) — the
 * "one operations view an operator opens when something might be wrong".
 *
 * Renders, from one polled `GET /api/v1/ops/overview` snapshot:
 *
 * - the nine Section 17 metrics (names/units per docs/plan/metrics.md) plus
 *   the worker/beat/sweeper heartbeats — the view never computes its own
 *   numbers; it displays the endpoint's document;
 * - all six Section 17 alerts (docs/plan/alerts.md) with firing state,
 *   severity and onset;
 * - the Health row (live/ready checks).
 *
 * Read-only by design (Section 17: acknowledgement/runbooks are out of
 * scope). Data freshness is displayed ("as of …") so a frozen view is
 * recognizable — the MT's explicit risk note. Update mode is polling; the
 * decision and cadence live in lib/queries/ops.ts.
 */

const METRIC_ROWS: ReadonlyArray<{
  key: string;
  label: string;
  unit: string;
  render: (metrics: Record<string, unknown>) => string;
}> = [
  {
    key: 'claims_per_minute',
    label: 'Claims per minute',
    unit: 'claims/min',
    render: (m) => formatNumber(m.claims_per_minute),
  },
  {
    key: 'claim_conflicts',
    label: 'Claim conflicts',
    unit: 'cumulative',
    render: (m) => formatNumber(m.claim_conflicts),
  },
  {
    key: 'active_leases',
    label: 'Active leases',
    unit: 'tasks',
    render: (m) => formatNumber(m.active_leases),
  },
  {
    key: 'lease_expirations',
    label: 'Lease expirations',
    unit: 'cumulative',
    render: (m) => formatNumber(m.lease_expirations),
  },
  {
    key: 'task_cycle_time_per_state',
    label: 'Task cycle time per state',
    unit: 'seconds (avg, 7-day)',
    render: (m) => formatMap(m.task_cycle_time_per_state),
  },
  {
    key: 'attachment_pipeline',
    label: 'Attachment pipeline',
    unit: 'terminal outcomes',
    render: (m) => formatAttachmentPipeline(m.attachment_pipeline),
  },
  {
    key: 'sse_connections',
    label: 'SSE connections',
    unit: 'connections',
    render: (m) => formatNumber(m.sse_connections),
  },
  {
    key: 'push_success_rate',
    label: 'Push success rate',
    unit: '% dispatched',
    render: (m) => formatRatio(m.push_success_rate),
  },
  {
    key: 'api_latency',
    label: 'API latency',
    unit: 'ms (avg)',
    render: (m) => formatLatency(m.api_latency),
  },
];

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function formatNumber(value: unknown): string {
  return typeof value === 'number' ? String(value) : '—';
}

function formatRatio(value: unknown): string {
  return typeof value === 'number' ? `${Math.round(value * 1000) / 10}%` : '—';
}

function formatMap(value: unknown): string {
  const entries = Object.entries(asRecord(value));
  if (entries.length === 0) {
    return '—';
  }
  return entries.map(([key, seconds]) => `${key}: ${formatNumber(seconds)}s`).join(' · ');
}

function formatAttachmentPipeline(value: unknown): string {
  const record = asRecord(value);
  const counts = asRecord(record.count_by_outcome);
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return '—';
  }
  const parts = entries.map(([outcome, count]) => `${outcome}: ${formatNumber(count)}`);
  const avg = record.duration_ms_avg;
  if (typeof avg === 'number') {
    parts.push(`avg ${avg}ms`);
  }
  return parts.join(' · ');
}

function formatLatency(value: unknown): string {
  const record = asRecord(value);
  const avg = record.duration_ms_avg;
  const count = record.count;
  if (typeof avg !== 'number') {
    return '—';
  }
  return `${avg}ms over ${formatNumber(count)} requests`;
}

function formatSeconds(value: unknown): string {
  if (typeof value !== 'number') {
    return 'never';
  }
  if (value < 90) {
    return `${Math.round(value)}s ago`;
  }
  return `${Math.round(value / 60)}m ago`;
}

function formatInstant(iso: unknown): string {
  if (typeof iso !== 'string' || iso === '') {
    return '—';
  }
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleTimeString();
}

function AlertBadge({ alert }: { alert: AlertState }) {
  const tone = alert.firing
    ? alert.severity === 'critical'
      ? 'bg-red-500/15 text-red-700 dark:text-red-400'
      : 'bg-amber-500/15 text-amber-800 dark:text-amber-400'
    : alert.status === 'unknown'
      ? 'bg-muted text-muted-foreground'
      : 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400';
  const label = alert.firing ? 'Firing' : alert.status === 'unknown' ? 'Unknown' : 'OK';
  return (
    <span
      data-testid={`alert-badge-${alert.id}`}
      data-firing={alert.firing ? 'true' : 'false'}
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}
    >
      {label}
    </span>
  );
}

function HeartbeatRow({ heartbeats }: { heartbeats: Record<string, unknown> }) {
  return (
    <ul className="flex flex-wrap gap-4 text-sm text-muted-foreground">
      {(['worker', 'beat', 'sweeper'] as const).map((kind) => (
        <li key={kind} data-testid={`heartbeat-${kind}`}>
          <span className="font-medium text-foreground">{kind}</span>:{' '}
          {formatSeconds(asRecord(heartbeats[kind]).age_seconds)}
        </li>
      ))}
    </ul>
  );
}

function HealthPanel({
  health,
  heartbeats,
}: {
  health: OpsHealth;
  heartbeats: Record<string, unknown>;
}) {
  return (
    <section
      aria-label="Health"
      className="rounded-lg border border-border bg-card p-4"
      data-testid="ops-health"
    >
      <h2 className="text-sm font-semibold text-card-foreground">Health</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {health.live ? 'Live' : 'Not live'} · database{' '}
        {health.checks.database === 'ok' ? 'reachable' : 'unreachable'} · cache{' '}
        {health.checks.cache === 'ok' ? 'reachable' : 'unreachable'}
      </p>
      <div className="mt-2">
        <HeartbeatRow heartbeats={heartbeats} />
      </div>
    </section>
  );
}

function MetricsPanel({ metrics }: { metrics: Record<string, unknown> }) {
  return (
    <section
      aria-label="Metrics"
      className="rounded-lg border border-border bg-card p-4"
      data-testid="ops-metrics"
    >
      <h2 className="text-sm font-semibold text-card-foreground">Metrics</h2>
      <dl className={layout.metricsGrid}>
        {METRIC_ROWS.map((row) => (
          <div key={row.key} className="flex flex-col" data-testid={`metric-${row.key}`}>
            <dt className="text-xs text-muted-foreground">
              {row.label} <span className="opacity-70">({row.unit})</span>
            </dt>
            <dd className="text-sm font-medium text-foreground">{row.render(metrics)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function AlertsPanel({ alerts }: { alerts: AlertState[] }) {
  return (
    <section
      aria-label="Alerts"
      className="rounded-lg border border-border bg-card p-4"
      data-testid="ops-alerts"
    >
      <h2 className="text-sm font-semibold text-card-foreground">Alerts</h2>
      <ul className="mt-2 divide-y divide-border">
        {alerts.map((alert) => (
          <li
            key={alert.id}
            data-testid={`alert-${alert.id}`}
            className="flex flex-wrap items-center gap-3 py-2"
          >
            <AlertBadge alert={alert} />
            <span className="text-sm font-medium text-foreground">{alert.name}</span>
            <span className="text-xs text-muted-foreground">
              since {formatInstant(alert.since)}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-muted-foreground">
        Acknowledgement, threshold tuning and runbooks are operator actions on the server — this
        view is read-only.
      </p>
    </section>
  );
}

export function OpsOverviewPanel() {
  const overview = useOpsOverviewQuery();

  if (overview.isPending) {
    return <LoadingState label="Loading operations snapshot…" />;
  }

  if (overview.isError) {
    const friendly = resolveError(overview.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void overview.refetch()}
      />
    );
  }

  const snapshot: OpsOverview = overview.data;
  const metrics = asRecord(snapshot.metrics);

  return (
    <div className="grid gap-4" data-testid="ops-overview">
      <p className="text-xs text-muted-foreground" data-testid="ops-freshness">
        As of {formatInstant(snapshot.generated_at)} (refreshes every 30 seconds)
      </p>
      <HealthPanel health={snapshot.health} heartbeats={asRecord(metrics.heartbeats)} />
      <AlertsPanel alerts={snapshot.alerts} />
      <MetricsPanel metrics={metrics} />
    </div>
  );
}
