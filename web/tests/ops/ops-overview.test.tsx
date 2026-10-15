/**
 * MT-6.4-03 — operations view component (Section 17 Dashboards row).
 *
 * Proves the MT's test command: metrics render with plan names/units and
 * alert states display for both resting and forced-firing fixtures —
 * through the real generated client (NFR-11), plus the loading and error
 * states and the freshness display the MT's risk note demands.
 */
import { screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { OpsOverviewPanel } from '@/components/ops/ops-overview';
import { errorResponse, installApi, jsonResponse, renderWithQueryClient } from '../helpers/api';

const OVERVIEW_ROUTE = {
  method: 'GET',
  match: /\/api\/v1\/ops\/overview(\?|$)/,
};

/** The nine Section 17 metrics + heartbeats, at their documented shapes. */
function makeMetrics() {
  return {
    claims_per_minute: 3,
    claim_conflicts: 7,
    active_leases: 2,
    lease_expirations: 11,
    task_cycle_time_per_state: { in_progress: 420.5 },
    attachment_pipeline: {
      count_by_outcome: { ready: 12, skipped: 1, failed: 0, gone: 0 },
      duration_ms_avg: 890.25,
    },
    sse_connections: 4,
    push_success_rate: 0.975,
    api_latency: {
      count: 1500,
      duration_ms_avg: 23.4,
      by_route: { 'GET /api/v1/projects 200': { count: 20, duration_ms_avg: 12.1 } },
    },
    heartbeats: {
      worker: { last_seen: '2026-10-14T10:00:00+00:00', age_seconds: 12 },
      beat: { last_seen: '2026-10-14T10:00:00+00:00', age_seconds: 30 },
      sweeper: { last_seen: '2026-10-14T10:00:00+00:00', age_seconds: 45 },
    },
  };
}

const ALERT_IDS = [
  'sweeper_not_running',
  'attachment_backlog',
  'push_failures',
  'tunnel_down',
  'repeated_auth_failures',
  'media_disk_usage',
] as const;

/** The six rules in plan order — resting: two ok, four unknown/ok mix. */
function makeAlerts(overrides: Partial<Record<string, Record<string, unknown>>> = {}) {
  return ALERT_IDS.map((id) => {
    const base: Record<string, unknown> = {
      id,
      name: {
        sweeper_not_running: 'Sweeper not running',
        attachment_backlog: 'Backlog of unprocessed attachments',
        push_failures: 'Push failures',
        tunnel_down: 'Tunnel down',
        repeated_auth_failures: 'Repeated auth failures',
        media_disk_usage: 'Disk usage on media volume',
      }[id],
      severity: id === 'attachment_backlog' || id === 'push_failures' ? 'warning' : 'critical',
      firing: false,
      status: id === 'tunnel_down' ? 'unknown' : 'ok',
      since: null,
      signal: {},
      threshold: {},
      runbook: null,
    };
    return { ...base, ...overrides[id] } as never;
  });
}

function makeOverview(alerts = makeAlerts(), metrics = makeMetrics()) {
  return {
    schema_version: 'ops-overview-1',
    generated_at: '2026-10-14T10:00:05+00:00',
    metrics,
    alerts,
    health: {
      live: true,
      checks: { database: 'ok', cache: 'ok' },
    },
  };
}

beforeEach(() => {
  vi.useRealTimers();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('OpsOverviewPanel', () => {
  it('renders all nine metrics with their plan names and units (resting fixture)', async () => {
    installApi([{ ...OVERVIEW_ROUTE, respond: () => jsonResponse(makeOverview()) }]);

    renderWithQueryClient(<OpsOverviewPanel />);

    await waitFor(() => expect(screen.getByTestId('ops-overview')).toBeTruthy());

    for (const [key, label] of [
      ['claims_per_minute', 'Claims per minute'],
      ['claim_conflicts', 'Claim conflicts'],
      ['active_leases', 'Active leases'],
      ['lease_expirations', 'Lease expirations'],
      ['task_cycle_time_per_state', 'Task cycle time per state'],
      ['attachment_pipeline', 'Attachment pipeline'],
      ['sse_connections', 'SSE connections'],
      ['push_success_rate', 'Push success rate'],
      ['api_latency', 'API latency'],
    ] as const) {
      const row = screen.getByTestId(`metric-${key}`);
      expect(row.textContent).toContain(label);
    }

    // Values from the document, not recomputed client-side.
    expect(screen.getByTestId('metric-claims_per_minute').textContent).toContain('3');
    expect(screen.getByTestId('metric-claim_conflicts').textContent).toContain('7');
    expect(screen.getByTestId('metric-push_success_rate').textContent).toContain('97.5%');
    expect(screen.getByTestId('metric-task_cycle_time_per_state').textContent).toContain(
      'in_progress: 420.5s',
    );
    expect(screen.getByTestId('metric-api_latency').textContent).toContain(
      '23.4ms over 1500 requests',
    );
    expect(screen.getByTestId('metric-attachment_pipeline').textContent).toContain('ready: 12');
  });

  it('displays all six alerts resting and the health row with heartbeats', async () => {
    installApi([{ ...OVERVIEW_ROUTE, respond: () => jsonResponse(makeOverview()) }]);

    renderWithQueryClient(<OpsOverviewPanel />);

    await waitFor(() => expect(screen.getByTestId('ops-alerts')).toBeTruthy());

    for (const id of ALERT_IDS) {
      const badge = screen.getByTestId(`alert-badge-${id}`);
      expect(badge.getAttribute('data-firing')).toBe('false');
      expect(badge.textContent).toBe(
        id === 'tunnel_down' ? 'Unknown' : 'OK', // tunnel never reported on a cold stack
      );
    }

    const health = screen.getByTestId('ops-health');
    expect(health.textContent).toContain('Live');
    expect(health.textContent).toContain('database reachable');
    expect(health.textContent).toContain('cache reachable');
    expect(screen.getByTestId('heartbeat-worker').textContent).toContain('12s ago');
    expect(screen.getByTestId('heartbeat-beat').textContent).toContain('30s ago');
    expect(screen.getByTestId('heartbeat-sweeper').textContent).toContain('45s ago');
  });

  it('surfaces a forced-firing alert with severity tone and since (firing fixture)', async () => {
    const firing = makeAlerts({
      sweeper_not_running: {
        firing: true,
        status: 'firing',
        severity: 'critical',
        since: '2026-10-14T09:55:00+00:00',
        signal: { heartbeat_age_seconds: 420 },
        threshold: { max_heartbeat_age_seconds: 180 },
      },
      push_failures: {
        firing: true,
        status: 'firing',
        severity: 'warning',
        since: '2026-10-14T09:50:00+00:00',
        signal: { success_rate_percent: 82.5, dispatched: 40 },
        threshold: { min_success_rate_percent: 90, min_dispatches: 10 },
      },
    });
    installApi([{ ...OVERVIEW_ROUTE, respond: () => jsonResponse(makeOverview(firing)) }]);

    renderWithQueryClient(<OpsOverviewPanel />);

    await waitFor(() => expect(screen.getByTestId('alert-sweeper_not_running')).toBeTruthy());

    const sweeperBadge = screen.getByTestId('alert-badge-sweeper_not_running');
    expect(sweeperBadge.getAttribute('data-firing')).toBe('true');
    expect(sweeperBadge.textContent).toBe('Firing');
    expect(screen.getByTestId('alert-sweeper_not_running').textContent).toContain(
      'Sweeper not running',
    );

    expect(screen.getByTestId('alert-badge-push_failures').textContent).toBe('Firing');
    // Resting neighbours stay resting in the same snapshot.
    expect(screen.getByTestId('alert-badge-attachment_backlog').textContent).toBe('OK');
  });

  it('shows data freshness from generated_at so a frozen view is recognizable', async () => {
    installApi([{ ...OVERVIEW_ROUTE, respond: () => jsonResponse(makeOverview()) }]);

    renderWithQueryClient(<OpsOverviewPanel />);

    const freshness = await screen.findByTestId('ops-freshness');
    expect(freshness.textContent).toContain('As of');
    expect(freshness.textContent).toContain('refreshes every 30 seconds');
  });

  it('shows a loading state while the snapshot is pending', async () => {
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    installApi([
      {
        ...OVERVIEW_ROUTE,
        respond: async () => {
          await gate;
          return jsonResponse(makeOverview());
        },
      },
    ]);

    renderWithQueryClient(<OpsOverviewPanel />);
    expect(screen.getByText('Loading operations snapshot…')).toBeTruthy();

    release?.();
    await waitFor(() => expect(screen.getByTestId('ops-overview')).toBeTruthy());
  });

  it('maps backend failures to catalog copy and never shows raw server text', async () => {
    installApi([
      {
        ...OVERVIEW_ROUTE,
        respond: () => errorResponse('SERVER_ERROR', 500, 'Traceback: very raw detail'),
      },
    ]);

    renderWithQueryClient(<OpsOverviewPanel />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.queryByText('Traceback: very raw detail')).toBeNull();
    expect(screen.getByText('Reference ID: corr-test')).toBeTruthy();
  });
});
