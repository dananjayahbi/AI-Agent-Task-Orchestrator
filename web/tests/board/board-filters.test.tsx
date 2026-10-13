/**
 * MT-4.3-03 — board filters, search and archive toggle (Section 13.1;
 * Section 8.2 T19 archive default; NFR-11 contract-only parameters).
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import {
  installApi,
  installBoardApi,
  jsonResponse,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

const ARCHIVED = makeTask({
  id: 'PID00001-T009',
  title: 'Archived cleanup task',
  archived_at: '2026-09-30T08:00:00Z',
});
const PLAIN = makeTask({ id: 'PID00001-T001', title: 'Plain pending task' });

const listCalls = (calls: Array<{ pathname: string; search: string }>) =>
  calls.filter((call) => call.pathname === '/api/v1/projects/PID00001/tasks');

function rawError(correlationId: string, message: string): Response {
  return new Response(
    JSON.stringify({
      error: {
        code: 'SERVER_ERROR',
        message,
        retryable: true,
        details: null,
        correlation_id: correlationId,
      },
    }),
    { status: 500, headers: { 'Content-Type': 'application/json' } },
  );
}

describe('Board filters (MT-4.3-03)', () => {
  it('hides archived tasks by default and reveals them only with the archive toggle (T19)', async () => {
    // A deliberately dumb tasks server: it ignores every filter, so the
    // assertions prove the *client* honors the T19 default as well.
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/tasks(\?|$)/,
        respond: () => jsonResponse(pageOf([PLAIN, ARCHIVED])),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
        respond: () => jsonResponse(makePolicy()),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => sseConnection().response,
      },
    ]);

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Plain pending task')).toBeTruthy());
    expect(screen.queryByText('Archived cleanup task')).toBeNull();
    expect(listCalls(calls)[0].search).not.toContain('include_archived=true');

    fireEvent.click(screen.getByTestId('board-archive-toggle'));
    await waitFor(() => expect(screen.getByText('Archived cleanup task')).toBeTruthy());
    expect(listCalls(calls).at(-1)?.search).toContain('include_archived=true');
  });

  it('applies the contract priority filter server-side and composes it with client-side search', async () => {
    const high = makeTask({ id: 'PID00001-T002', title: 'Alpha high task', priority: 'high' });
    const low = makeTask({ id: 'PID00001-T003', title: 'Beta low task', priority: 'low' });
    const { calls } = installBoardApi({
      tasks: [high, low],
      sse: () => sseConnection().response,
    });

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Alpha high task')).toBeTruthy());

    fireEvent.change(screen.getByTestId('board-priority-filter'), {
      target: { value: 'high' },
    });
    await waitFor(() => {
      expect(screen.queryByText('Beta low task')).toBeNull();
      expect(screen.getByText('Alpha high task')).toBeTruthy();
    });
    expect(listCalls(calls).at(-1)?.search).toContain('priority=high');

    // Search narrows the loaded set client-side — no extra server call.
    const before = listCalls(calls).length;
    fireEvent.change(screen.getByTestId('board-search'), { target: { value: 'zzz-no-match' } });
    await waitFor(() =>
      expect(screen.getByText('No tasks match the current filters')).toBeTruthy(),
    );
    expect(listCalls(calls)).toHaveLength(before);
  });

  it('filters by canonical state through the contract parameter and empties hidden columns', async () => {
    const draft = makeTask({ id: 'PID00001-T001', title: 'Draft entry', state: 'draft' });
    const pending = makeTask({ id: 'PID00001-T002', title: 'Pending entry', state: 'pending' });
    const { calls } = installBoardApi({
      tasks: [draft, pending],
      sse: () => sseConnection().response,
    });

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Draft entry')).toBeTruthy());

    fireEvent.click(screen.getByTestId('board-state-filter-draft'));
    await waitFor(() => {
      expect(screen.queryByText('Draft entry')).toBeNull();
      expect(screen.getByTestId('board-column-empty-draft')).toBeTruthy();
    });

    const lastSearch = listCalls(calls).at(-1)?.search ?? '';
    expect(lastSearch).toContain('state=pending');
    expect(lastSearch).not.toContain('state=draft');
  });

  it('shows the filtered-empty state (distinct from loading/error) with a clear action', async () => {
    installBoardApi({
      tasks: [PLAIN],
      sse: () => sseConnection().response,
    });

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Plain pending task')).toBeTruthy());

    fireEvent.change(screen.getByTestId('board-search'), { target: { value: 'nothing-matches' } });
    await waitFor(() =>
      expect(screen.getByText('No tasks match the current filters')).toBeTruthy(),
    );
    expect(screen.queryByText('Loading board…')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();

    fireEvent.click(screen.getByTestId('board-empty-clear-filters'));
    await waitFor(() => expect(screen.getByText('Plain pending task')).toBeTruthy());
    expect((screen.getByTestId('board-search') as HTMLInputElement).value).toBe('');
  });

  it('composes filters, then clears them all back to the documented defaults', async () => {
    const { calls } = installBoardApi({
      tasks: [
        PLAIN,
        makeTask({ id: 'PID00001-T002', title: 'Urgent one', priority: 'urgent' }),
        ARCHIVED,
      ],
      sse: () => sseConnection().response,
    });

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Plain pending task')).toBeTruthy());

    fireEvent.change(screen.getByTestId('board-priority-filter'), { target: { value: 'urgent' } });
    fireEvent.click(screen.getByTestId('board-archive-toggle'));
    fireEvent.click(screen.getByTestId('board-state-filter-completed'));
    fireEvent.change(screen.getByTestId('board-search'), { target: { value: 'one' } });
    await waitFor(() => {
      expect(screen.getByText('Urgent one')).toBeTruthy();
      expect(screen.queryByText('Plain pending task')).toBeNull();
    });

    const callsBeforeClear = listCalls(calls).length;
    fireEvent.click(screen.getByTestId('board-clear-filters'));
    await waitFor(() => expect(screen.getByText('Plain pending task')).toBeTruthy());
    // Clearing restores the T19 default: archived tasks are hidden again,
    // while the unfiltered set (including the urgent task) is back.
    expect(screen.getByText('Urgent one')).toBeTruthy();
    expect(screen.queryByText('Archived cleanup task')).toBeNull();
    // The default view is the cached first-load entry (Section 13.3 query
    // caching, staleTime 30 s) — no refetch, so the last request stays the
    // last *filtered* one and the cached data renders immediately.
    expect(listCalls(calls)).toHaveLength(callsBeforeClear);

    const last = listCalls(calls).at(-1)?.search ?? '';
    expect(last).toContain('priority=urgent'); // the last server call was the filtered one
    expect((screen.getByTestId('board-search') as HTMLInputElement).value).toBe('');
    expect((screen.getByTestId('board-priority-filter') as HTMLSelectElement).value).toBe('');
    expect((screen.getByTestId('board-state-filter-completed') as HTMLInputElement).checked).toBe(
      true,
    );
    expect((screen.getByTestId('board-archive-toggle') as HTMLInputElement).checked).toBe(false);
    expect(screen.getByTestId('board-clear-filters')).toHaveProperty('disabled', true);
  });

  it('maps refetch errors under a new filter to canonical catalog copy', async () => {
    let failHigh = false;
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/tasks(\?|$)/,
        respond: ({ search }) => {
          if (failHigh && search.includes('priority=high')) {
            return rawError('corr-filter', 'raw db trace');
          }
          return jsonResponse(pageOf([PLAIN]));
        },
      },
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
        respond: () => jsonResponse(makePolicy()),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => sseConnection().response,
      },
    ]);

    renderWithQueryClient(<Board pid="PID00001" />);
    await waitFor(() => expect(screen.getByText('Plain pending task')).toBeTruthy());

    failHigh = true;
    fireEvent.change(screen.getByTestId('board-priority-filter'), { target: { value: 'high' } });
    await waitFor(() =>
      expect(
        screen.getByText(
          'The server had a problem handling this request. Try again — if it keeps failing, share the reference ID with support.',
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText('raw db trace')).toBeNull();
    expect(screen.getByText('Reference ID: corr-filter')).toBeTruthy();
  });
});
