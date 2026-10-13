/**
 * MT-4.5-04 — dependencies picker: project-scoped lazy choices (no eager
 * full-project fetch), search over loaded pages, add/remove with
 * self/duplicate exclusion, per-dependency state badges (Section 8.2
 * T2/T4 visibility), save→reload round trip, and catalog error mapping
 * (Section 13.3).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
} from '../helpers/api';
import type { Route } from '../helpers/api';

const PID = 'PID00001';

beforeEach(() => {
  vi.unstubAllGlobals();
});

/**
 * One `GET /projects/{pid}/tasks` route that plays both roles: the board
 * asks for `page_size=100` (its documented clamp), the picker for
 * `page_size=25` with cursors — the query string tells them apart.
 */
function listRoute(options: {
  boardTasks: unknown[];
  choiceTasks: unknown[];
  choicePageSize?: number;
}): Route {
  const pageSize = options.choicePageSize ?? 25;
  return {
    method: 'GET',
    match: new RegExp(`/api/v1/projects/${PID}/tasks(\\?|$)`),
    respond: ({ search }) => {
      const params = new URLSearchParams(search);
      if (params.get('page_size') === String(pageSize)) {
        const cursor = params.get('cursor');
        const start = cursor === null ? 0 : Number(cursor);
        const slice = options.choiceTasks.slice(start, start + pageSize);
        const next =
          start + pageSize < options.choiceTasks.length ? String(start + pageSize) : null;
        return jsonResponse(pageOf(slice, next));
      }
      return jsonResponse(pageOf(options.boardTasks));
    },
  };
}

function taskRowRoute(tasks: unknown[]): Route {
  return {
    method: 'GET',
    match: /\/api\/v1\/tasks\/PID00001-T0\d\d(\?|$)/,
    respond: ({ pathname }) => {
      const id = pathname.split('/').pop() ?? '';
      const row = tasks.find((task) => (task as { id: string }).id === id);
      return row === undefined ? errorResponse('TASK_NOT_FOUND', 404) : jsonResponse(row);
    },
  };
}

/** Policy + SSE extras the board always asks for (quiet console). */
const boardExtras: Route[] = [
  {
    method: 'GET',
    match: new RegExp(`/api/v1/projects/${PID}/policy(\\?|$)`),
    respond: () => jsonResponse(makePolicy()),
  },
  {
    method: 'GET',
    match: /\/api\/v1\/events\/stream(\?|$)/,
    respond: () => sseConnection().response,
  },
];

describe('dependencies-picker', () => {
  it('lists only the bound project tasks, lazily paged — no eager full fetch', async () => {
    const all = Array.from({ length: 30 }, (_, i) =>
      makeTask({ id: `PID00001-T${String(i + 1).padStart(3, '0')}`, title: `Task ${i + 1}` }),
    );
    const { calls } = installApi([
      listRoute({
        boardTasks: [makeTask({ id: 'PID00001-T050', state: 'draft' })],
        choiceTasks: all,
      }),
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/OTHER99\/tasks(\?|$)/,
        respond: () => {
          throw new Error('cross-project bleed');
        },
      },
      ...boardExtras,
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T050'));
    const picker = within(screen.getByTestId('dependencies-picker'));

    // Exactly one page loaded (25 of 30) — no full-project fetch.
    await waitFor(() => expect(picker.getByTestId('dependency-add-PID00001-T001')).toBeTruthy());
    expect(picker.queryByTestId('dependency-add-PID00001-T026')).toBeNull();
    expect(picker.getByTestId('dependencies-load-more')).toBeTruthy();
    const listCalls = calls.filter(
      (call) =>
        call.method === 'GET' &&
        call.pathname === `/api/v1/projects/${PID}/tasks` &&
        call.search.includes('page_size=25'),
    );
    expect(listCalls).toHaveLength(1);
    expect(listCalls[0]?.search).toContain('page_size=25');

    fireEvent.click(picker.getByTestId('dependencies-load-more'));
    await waitFor(() => expect(picker.getByTestId('dependency-add-PID00001-T030')).toBeTruthy());

    // Self is never offered, even after loading every page.
    expect(picker.queryByTestId('dependency-add-PID00001-T050')).toBeNull();
  });

  it('searches loaded choices by id or title and hides already-selected rows', async () => {
    const all = [
      makeTask({ id: 'PID00001-T001', title: 'Design the schema' }),
      makeTask({ id: 'PID00001-T002', title: 'Write migrations' }),
    ];
    installApi([
      listRoute({
        boardTasks: [makeTask({ id: 'PID00001-T050', state: 'draft' })],
        choiceTasks: all,
      }),
      ...boardExtras,
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T050'));
    const picker = within(screen.getByTestId('dependencies-picker'));

    fireEvent.change(screen.getByLabelText('Search tasks to add as dependencies'), {
      target: { value: 'migration' },
    });
    await waitFor(() => expect(picker.getByTestId('dependency-add-PID00001-T002')).toBeTruthy());
    expect(picker.queryByTestId('dependency-add-PID00001-T001')).toBeNull();

    // Selecting removes the row from the choices (no duplicates possible).
    fireEvent.click(picker.getByTestId('dependency-add-PID00001-T002'));
    expect(picker.queryByTestId('dependency-add-PID00001-T002')).toBeNull();
    expect(picker.getByTestId('dependency-chip-PID00001-T002')).toBeTruthy();
  });

  it('shows each dependency state and saves/removes the set through the round trip', async () => {
    const completed = makeTask({ id: 'PID00001-T003', state: 'completed', title: 'Done deal' });
    const tasks: unknown[] = [
      makeTask({
        id: 'PID00001-T051',
        state: 'draft',
        depends_on: ['PID00001-T003'],
        version: 4,
      }),
      completed,
    ];
    const { calls } = installApi([
      listRoute({ boardTasks: tasks, choiceTasks: tasks }),
      taskRowRoute(tasks),
      ...boardExtras,
      {
        method: 'PATCH',
        match: /\/api\/v1\/tasks\/PID00001-T051$/,
        respond: ({ body }) => {
          const patched = body as { depends_on: string[] };
          tasks[0] = makeTask({
            id: 'PID00001-T051',
            state: 'draft',
            depends_on: patched.depends_on,
            version: 5,
          });
          return jsonResponse(tasks[0]);
        },
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T051'));
    // Existing dependency shows its live state (T2 visibility).
    await waitFor(() =>
      expect(screen.getByTestId('dependency-chip-state-PID00001-T003').textContent).toBe(
        'Completed',
      ),
    );

    // Remove it — the set clears server-side.
    fireEvent.click(screen.getByTestId('dependency-remove-PID00001-T003'));
    fireEvent.click(screen.getByTestId('task-form-submit'));
    await waitFor(() => expect(screen.getByText('Changes saved.')).toBeTruthy());
    const patch = calls.find((call) => call.method === 'PATCH');
    expect(patch?.body).toMatchObject({ depends_on: [], version: 4 });

    // Reload: the saved (empty) set is what comes back.
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());
    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T051'));
    expect(screen.queryByTestId('dependency-chip-PID00001-T003')).toBeNull();
  });

  it('maps DEPENDENCY_UNMET from a save to the friendly catalog message', async () => {
    const tasks: unknown[] = [
      makeTask({ id: 'PID00001-T052', state: 'draft', depends_on: ['PID00001-T004'] }),
      makeTask({ id: 'PID00001-T004', state: 'pending', title: 'Blocking task' }),
    ];
    installApi([
      listRoute({ boardTasks: tasks, choiceTasks: tasks }),
      taskRowRoute(tasks),
      ...boardExtras,
      {
        method: 'PATCH',
        match: /\/api\/v1\/tasks\/PID00001-T052$/,
        respond: () => errorResponse('DEPENDENCY_UNMET', 409),
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T052'));
    // Non-completed dependency is visible before publish time.
    await waitFor(() =>
      expect(screen.getByTestId('dependency-chip-state-PID00001-T004').textContent).toBe('Pending'),
    );

    fireEvent.change(within(screen.getByTestId('task-form-modal')).getByLabelText('Title'), {
      target: { value: 'Renamed' },
    });
    fireEvent.click(screen.getByTestId('task-form-submit'));

    expect(
      await screen.findByText("This task can't start until its dependencies are complete."),
    ).toBeTruthy();
    expect(screen.getByTestId('task-form-modal')).toBeTruthy();
  });

  it('never offers the edited task as its own dependency (self-guard)', async () => {
    installApi([
      listRoute({
        boardTasks: [makeTask({ id: 'PID00001-T053', state: 'draft' })],
        choiceTasks: [makeTask({ id: 'PID00001-T053', title: 'Me' })],
      }),
      ...boardExtras,
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T053'));
    const picker = within(screen.getByTestId('dependencies-picker'));
    await waitFor(() => expect(picker.getByTestId('dependencies-empty')).toBeTruthy());
    expect(picker.queryByTestId('dependency-add-PID00001-T053')).toBeNull();
  });
});
