/**
 * MT-4.10-01 — audit log viewer (Sections 13.1, 9.2, 12.5, ADR-010).
 *
 * Pins: fixture rendering of every published field (canonical type +
 * friendly label, server instant, actor, project/task links, event id),
 * unknown/forward types rendering raw, collapsed-by-default payload
 * expansion, cursor pagination beyond one page through the bounded
 * helper, strictly read-only controls, the contract-only filter
 * parameters, and the separated loading/empty/error states.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuditLogView } from '@/components/audit/audit-log-view';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  pageOf,
  renderWithQueryClient,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

const eventClaim = makeEventEnvelope({
  id: 1,
  type: 'task.claimed',
  project_id: 'PID00001',
  task_id: 'PID00001-T001',
  occurred_at: '2026-10-01T09:00:00Z',
  actor: { type: 'agent', ref: 'sess-1' },
  data: { reason_code: 'claim', task_version: 2 },
});

const eventAudit = makeEventEnvelope({
  id: 2,
  type: 'audit.passed',
  project_id: 'PID00001',
  task_id: 'PID00001-T001',
  occurred_at: '2026-10-01T10:00:00Z',
  actor: { type: 'agent', ref: 'sess-2' },
  data: { confidence: 5 },
});

const eventForward = makeEventEnvelope({
  id: 3,
  type: 'future.forward_type',
  project_id: 'PID00001',
  task_id: null,
  occurred_at: '2026-10-01T11:00:00Z',
  actor: { type: 'system', ref: 'forward-server' },
  data: { anything: true },
});

function setupAuditLog(options: {
  pages?: Array<{ results: unknown[]; next: string | null }>;
  error?: boolean;
  filters?: { project: string | null; task: string | null };
}): { calls: Array<{ pathname: string; search: string }> } {
  const pages = options.pages ?? [{ results: [], next: null }];
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/events(\?|$)/,
      respond: ({ search }) => {
        if (options.error === true) {
          return errorResponse('SERVER_ERROR', 500);
        }
        const params = new URLSearchParams(search);
        const cursor = params.get('cursor');
        const index = cursor === null ? 0 : Number(cursor);
        const page = pages[index] ?? { results: [], next: null };
        return jsonResponse(pageOf(page.results, page.next));
      },
    },
  ]);
  renderWithQueryClient(<AuditLogView filters={options.filters} />);
  return { calls };
}

describe('Audit log viewer (MT-4.10-01)', () => {
  it('renders every published field with canonical type beside its label, and unknown types raw', async () => {
    setupAuditLog({ pages: [{ results: [eventClaim, eventAudit, eventForward], next: null }] });

    const list = await screen.findByTestId('audit-log-list');
    const entries = within(list).getAllByTestId('audit-event-entry');
    // Newest first (the endpoint pages oldest → newest; the view reverses).
    expect(entries.map((entry) => entry.getAttribute('data-event-type'))).toEqual([
      'future.forward_type',
      'audit.passed',
      'task.claimed',
    ]);

    const claim = entries[2];
    // ADR-010: friendly label AND the canonical string — never one instead.
    expect(within(claim).getByText('Task claimed')).toBeTruthy();
    expect(within(claim).getByText('task.claimed')).toBeTruthy();
    expect(within(claim).getByText('2026-10-01T09:00:00Z')).toBeTruthy();
    expect(within(claim).getByText('agent · sess-1')).toBeTruthy();
    expect(within(claim).getByRole('link', { name: 'PID00001' })).toBeTruthy();
    const taskLink = within(claim).getByRole('link', { name: 'PID00001-T001' });
    expect(taskLink.getAttribute('href')).toBe('/projects/PID00001/tasks/PID00001-T001');
    expect(within(claim).getByText('#1')).toBeTruthy();

    // Forward/unknown types render raw — no label, no crash (20.4 item 6).
    const forward = entries[0];
    expect(within(forward).getByText('future.forward_type')).toBeTruthy();
    expect(within(forward).getByText('#3')).toBeTruthy();
  });

  it('keeps payloads collapsed by default and renders the JSON only when expanded (RISK-13)', async () => {
    setupAuditLog({ pages: [{ results: [eventClaim], next: null }] });
    const entry = await screen.findByTestId('audit-event-entry');
    expect(screen.queryByTestId('audit-event-payload')).toBeNull();

    fireEvent.click(within(entry).getByRole('button', { name: 'Show payload' }));
    const payload = screen.getByTestId('audit-event-payload');
    expect(payload.textContent).toContain('"reason_code": "claim"');
    expect(payload.textContent).toContain('"task_version": 2');

    fireEvent.click(within(entry).getByRole('button', { name: 'Hide payload' }));
    expect(screen.queryByTestId('audit-event-payload')).toBeNull();
  });

  it('follows the cursor beyond one page (bounded helper) and merges newest-first', async () => {
    const { calls } = setupAuditLog({
      pages: [
        { results: [eventClaim, eventAudit], next: '1' },
        { results: [eventForward], next: null },
      ],
    });

    const entries = await screen.findAllByTestId('audit-event-entry');
    expect(entries).toHaveLength(3);
    expect(entries[0].getAttribute('data-event-type')).toBe('future.forward_type');
    await waitFor(() => expect(calls.some((call) => call.search.includes('cursor=1'))).toBe(true));
    expect(calls.filter((call) => call.pathname === '/api/v1/events')).toHaveLength(2);
  });

  it('is strictly read-only — no mutation affordances anywhere (Section 12.5)', async () => {
    setupAuditLog({ pages: [{ results: [eventClaim, eventAudit], next: null }] });
    await screen.findAllByTestId('audit-event-entry');
    expect(
      screen.queryByRole('button', { name: /delete|edit|remove|revoke|save|update/i }),
    ).toBeNull();
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('sends only the contract filter parameters (no invented filters)', async () => {
    const { calls } = setupAuditLog({
      pages: [{ results: [eventClaim], next: null }],
      filters: { project: 'PID00001', task: 'PID00001-T001' },
    });
    await screen.findByTestId('audit-event-entry');
    const call = calls.find((candidate) => candidate.pathname === '/api/v1/events');
    expect(call).toBeDefined();
    const params = new URLSearchParams(call?.search ?? '');
    expect(params.get('project')).toBe('PID00001');
    expect(params.get('task')).toBe('PID00001-T001');
    expect(params.get('page_size')).toBe('100');
    for (const invented of ['actor', 'type', 'from', 'to', 'date']) {
      expect(params.has(invented)).toBe(false);
    }
  });

  it('shows the empty state when the log has no events', async () => {
    setupAuditLog({ pages: [{ results: [], next: null }] });
    expect(await screen.findByText('No events yet')).toBeTruthy();
  });

  it('shows catalog-only error copy on a failed history fetch', async () => {
    setupAuditLog({ error: true });
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
  });
});
