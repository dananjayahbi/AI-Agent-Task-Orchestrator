/**
 * MT-4.10-02 — audit log filters (Sections 13.1, 19, 9.2, 20.4 item 4).
 *
 * Pins: per-dimension parameter mapping for the two contract-published
 * dimensions (project, task), their composition, URL round-trip
 * (refresh/share reproduces the view), pagination reset on filter
 * change, the distinct filtered-empty state with clear-all, catalog-only
 * type options with the disabled-dimension contract note, and chips with
 * individual clear.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AuditLog } from '@/components/audit/audit-log';
import { EVENT_CATALOG } from '@/lib/stream/event-catalog';
import {
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makeProject,
  pageOf,
  renderWithQueryClient,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  window.history.replaceState(null, '', '/audit-log');
});

const eventClaim = makeEventEnvelope({
  id: 1,
  type: 'task.claimed',
  project_id: 'PID00001',
  task_id: 'PID00001-T001',
  occurred_at: '2026-10-01T09:00:00Z',
  actor: { type: 'agent', ref: 'sess-1' },
  data: {},
});

const eventAudit = makeEventEnvelope({
  id: 2,
  type: 'audit.passed',
  project_id: 'PID00001',
  task_id: 'PID00001-T001',
  occurred_at: '2026-10-01T10:00:00Z',
  actor: { type: 'agent', ref: 'sess-2' },
  data: {},
});

type RecordedCall = { pathname: string; search: string };

function setupAuditLog(): { calls: RecordedCall[]; unmount: () => void } {
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/projects(\?|$)/,
      respond: () =>
        jsonResponse(
          pageOf([
            makeProject({ id: 'PID00001', name: 'Alpha' }),
            makeProject({ id: 'PID00002', name: 'Beta' }),
          ]),
        ),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events(\?|$)/,
      respond: ({ search }) => {
        const params = new URLSearchParams(search);
        const project = params.get('project');
        const cursor = params.get('cursor');
        if (project === 'PID00002') {
          return jsonResponse(pageOf([])); // Beta has no recorded events
        }
        if (cursor === null) {
          return jsonResponse(pageOf([eventClaim], '1'));
        }
        return jsonResponse(pageOf([eventAudit], null));
      },
    },
  ]);
  const rendered = renderWithQueryClient(<AuditLog />);
  return { calls, unmount: rendered.unmount };
}

const eventCalls = (calls: RecordedCall[]) =>
  calls.filter((call) => call.pathname === '/api/v1/events');

describe('Audit log filters (MT-4.10-02)', () => {
  it('maps the project filter to the contract parameter and restarts pagination from page one', async () => {
    const { calls } = setupAuditLog();
    await screen.findAllByTestId('audit-event-entry');
    // Unfiltered load followed the cursor (two pages).
    expect(eventCalls(calls)).toHaveLength(2);

    const select = screen.getByTestId('audit-filter-project') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: 'PID00002' } });

    await waitFor(() =>
      expect(
        eventCalls(calls).some(
          (call) => call.search.includes('project=PID00002') && !call.search.includes('cursor='),
        ),
      ).toBe(true),
    );
    expect(window.location.search).toContain('project=PID00002');
  });

  it('composes project + task into the documented parameters and round-trips through the URL', async () => {
    const { calls, unmount } = setupAuditLog();
    await screen.findAllByTestId('audit-event-entry');

    fireEvent.change(screen.getByTestId('audit-filter-project'), {
      target: { value: 'PID00001' },
    });
    const taskInput = screen.getByTestId('audit-filter-task');
    fireEvent.change(taskInput, { target: { value: 'PID00001-T007' } });
    fireEvent.keyDown(taskInput, { key: 'Enter' });

    await waitFor(() =>
      expect(
        eventCalls(calls).some(
          (call) =>
            call.search.includes('project=PID00001') && call.search.includes('task=PID00001-T007'),
        ),
      ).toBe(true),
    );
    expect(window.location.search).toContain('project=PID00001');
    expect(window.location.search).toContain('task=PID00001-T007');

    // Refresh/share round-trip: a fresh mount restores filters from the URL.
    unmount();
    renderWithQueryClient(<AuditLog />);
    const select = (await screen.findByTestId('audit-filter-project')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('PID00001'));
    expect((screen.getByTestId('audit-filter-task') as HTMLInputElement).value).toBe(
      'PID00001-T007',
    );
  });

  it('shows the distinct filtered-empty state with a reset that restores the full list', async () => {
    const { calls } = setupAuditLog();
    await screen.findAllByTestId('audit-event-entry');

    fireEvent.change(screen.getByTestId('audit-filter-project'), {
      target: { value: 'PID00002' },
    });

    expect(await screen.findByText('No events match these filters')).toBeTruthy();
    expect(screen.queryByText('No events yet')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));

    expect((await screen.findAllByTestId('audit-event-entry')).length).toBeGreaterThan(0);
    expect(window.location.search).toBe('');
    const select = screen.getByTestId('audit-filter-project') as HTMLSelectElement;
    expect(select.value).toBe('');
    await waitFor(() =>
      expect(eventCalls(calls).some((call) => call.search === '?page_size=100')).toBe(true),
    );
  });

  it('limits type options to the Section 9.6 catalog and disables unbacked dimensions with the contract note', async () => {
    setupAuditLog();
    await screen.findAllByTestId('audit-event-entry');

    const typeSelect = screen.getByTestId('audit-filter-type') as HTMLSelectElement;
    expect(typeSelect.disabled).toBe(true);
    const values = Array.from(typeSelect.options)
      .map((option) => option.value)
      .filter((value) => value !== '');
    expect(values).toEqual([...EVENT_CATALOG]);

    expect((screen.getByTestId('audit-filter-actor') as HTMLSelectElement).disabled).toBe(true);
    expect((screen.getByTestId('audit-filter-from') as HTMLInputElement).disabled).toBe(true);
    expect((screen.getByTestId('audit-filter-to') as HTMLInputElement).disabled).toBe(true);

    const note = screen.getByTestId('audit-filter-contract-note');
    expect(note.textContent).toContain('contract change');
    expect(note.textContent).toContain('project');
    expect(note.textContent).toContain('task');
  });

  it('summarizes active filters as chips with individual clear and clear-all', async () => {
    const { calls } = setupAuditLog();
    await screen.findAllByTestId('audit-event-entry');

    fireEvent.change(screen.getByTestId('audit-filter-project'), {
      target: { value: 'PID00001' },
    });
    const taskInput = screen.getByTestId('audit-filter-task');
    fireEvent.change(taskInput, { target: { value: 'PID00001-T001' } });
    fireEvent.keyDown(taskInput, { key: 'Enter' });

    const chips = await screen.findByTestId('audit-filter-chips');
    expect(within(chips).getByText('PID00001')).toBeTruthy();
    expect(within(chips).getByText('PID00001-T001')).toBeTruthy();

    fireEvent.click(within(chips).getByRole('button', { name: 'Clear Task filter' }));
    await waitFor(() => expect(window.location.search).not.toContain('task='));
    expect(window.location.search).toContain('project=PID00001');
    // The input remounts empty — a draft can never outlive the URL.
    expect((screen.getByTestId('audit-filter-task') as HTMLInputElement).value).toBe('');

    const chipsAfter = screen.getByTestId('audit-filter-chips');
    fireEvent.click(within(chipsAfter).getByRole('button', { name: 'Clear all' }));
    await waitFor(() => expect(window.location.search).toBe(''));
    expect(screen.queryByTestId('audit-filter-chips')).toBeNull();
    await waitFor(() =>
      expect(eventCalls(calls).filter((call) => call.search === '?page_size=100').length).toBe(1),
    );
  });
});
