/**
 * MT-4.5-01 — task form modal: scaffold completeness (Section 13.2 field
 * set), core-field validation from the shared schemas, create → `draft`
 * (T1), edit round trip through PATCH with the `version` the client saw,
 * canonical error mapping to friendly copy (Section 13.3), unsaved-change
 * protection and keyboard operation (Section 13.4).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import {
  makeTask,
  renderWithQueryClient,
  tasksServerRoute,
  installApi,
  jsonResponse,
} from '../helpers/api';
import type { Route } from '../helpers/api';

const PID = 'PID00001';

beforeEach(() => {
  vi.unstubAllGlobals();
});

function errorEnvelope(code: string, status: number, details: unknown = null): Response {
  return jsonResponse(
    {
      error: {
        code,
        message: `${code} from the test server.`,
        retryable: status >= 500,
        details,
        correlation_id: 'corr-test',
      },
    },
    status,
  );
}

function boardWith(tasks: unknown[], extraRoutes: Route[] = []) {
  return installApi([tasksServerRoute(PID, tasks), ...extraRoutes]);
}

async function openCreateModal() {
  fireEvent.click(await screen.findByTestId('board-new-task'));
  await waitFor(() => expect(screen.getByTestId('task-form-modal')).toBeTruthy());
}

describe('task-form-modal', () => {
  it('exposes the full Section 13.2 field set as a wired scaffold', async () => {
    boardWith([]);
    renderWithQueryClient(<Board pid={PID} />);
    await openCreateModal();

    // Core fields implemented here (MT-4.5-01 scope).
    const modal = within(screen.getByTestId('task-form-modal'));
    expect(modal.getByLabelText('Title')).toBeTruthy();
    expect(modal.getByLabelText('Test command')).toBeTruthy();
    expect(modal.getByLabelText('Priority')).toBeTruthy();
    // Scaffold regions the later slices fill in — stable testids.
    for (const section of ['description', 'criteria', 'scope', 'dependencies', 'attachments']) {
      expect(screen.getByTestId(`task-form-section-${section}`)).toBeTruthy();
    }
    expect(screen.getByTestId('task-form-submit').textContent).toBe('Create draft task');
  });

  it('validates the required title locally and never posts an invalid payload', async () => {
    const { calls } = boardWith([]);
    renderWithQueryClient(<Board pid={PID} />);
    await openCreateModal();

    fireEvent.click(screen.getByTestId('task-form-submit'));

    expect(
      await within(screen.getByTestId('task-form-modal')).findByText('A title is required.'),
    ).toBeTruthy();
    expect(calls.filter((call) => call.method === 'POST')).toHaveLength(0);
  });

  it('creates via POST /projects/{pid}/tasks and the task lands as a draft card (T1)', async () => {
    const tasks: unknown[] = [];
    const { calls } = boardWith(tasks, [
      {
        method: 'POST',
        match: new RegExp(`/api/v1/projects/${PID}/tasks$`),
        respond: () => {
          const created = makeTask({
            id: 'PID00001-T001',
            title: 'Wire the login form',
            state: 'draft',
            version: 1,
          });
          tasks.push(created);
          return jsonResponse(created, 201);
        },
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);
    await openCreateModal();

    fireEvent.change(within(screen.getByTestId('task-form-modal')).getByLabelText('Title'), {
      target: { value: 'Wire the login form' },
    });
    fireEvent.click(screen.getByTestId('task-form-submit'));

    const card = await screen.findByTestId('task-card');
    expect(card.getAttribute('aria-label')).toBe('PID00001-T001');
    const draftColumn = screen.getByTestId('board-column-draft');
    expect(within(draftColumn).getByTestId('task-card')).toBeTruthy();

    const create = calls.find((call) => call.method === 'POST');
    expect(create?.pathname).toBe(`/api/v1/projects/${PID}/tasks`);
    expect(create?.body).toMatchObject({ title: 'Wire the login form', priority: 'medium' });
    // T1: `state`/`version` are server-owned — never sent by the client.
    expect(create?.body).not.toHaveProperty('state');
    expect(create?.body).not.toHaveProperty('version');
  });

  it('opens the same modal from a card in edit mode and saves via PATCH with the version it saw', async () => {
    const task = makeTask({ id: 'PID00001-T002', title: 'Old title', version: 7, state: 'draft' });
    const { calls } = boardWith(
      [task],
      [
        {
          method: 'PATCH',
          match: /\/api\/v1\/tasks\/PID00001-T002$/,
          respond: () => jsonResponse(makeTask({ ...task, title: 'New title', version: 8 })),
        },
      ],
    );
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T002'));
    await waitFor(() => expect(screen.getByTestId('task-form-modal')).toBeTruthy());
    expect(screen.getByDisplayValue('Old title')).toBeTruthy();

    fireEvent.change(within(screen.getByTestId('task-form-modal')).getByLabelText('Title'), {
      target: { value: 'New title' },
    });
    fireEvent.click(screen.getByTestId('task-form-submit'));

    await waitFor(() => expect(screen.getByText('Changes saved.')).toBeTruthy());
    const patch = calls.find((call) => call.method === 'PATCH');
    expect(patch?.body).toMatchObject({ title: 'New title', version: 7 });
  });

  it('maps a server VALIDATION_ERROR to field-level friendly feedback and stays open', async () => {
    const task = makeTask({ id: 'PID00001-T003', state: 'draft' });
    const { calls } = boardWith(
      [task],
      [
        {
          method: 'PATCH',
          match: /\/api\/v1\/tasks\/PID00001-T003$/,
          respond: () => errorEnvelope('VALIDATION_ERROR', 400, { title: ['blank not allowed'] }),
        },
      ],
    );
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T003'));
    fireEvent.click(screen.getByTestId('task-form-submit'));

    expect(
      await screen.findByText(
        "Some of the information you provided isn't valid. Review the fields and try again.",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText('The server rejected this value. Review it and try again.'),
    ).toBeTruthy();
    // Modal stays open for correction.
    expect(screen.getByTestId('task-form-modal')).toBeTruthy();
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(1);
  });

  it('maps VERSION_CONFLICT to friendly refresh guidance', async () => {
    const task = makeTask({ id: 'PID00001-T004', state: 'draft' });
    boardWith(
      [task],
      [
        {
          method: 'PATCH',
          match: /\/api\/v1\/tasks\/PID00001-T004$/,
          respond: () => errorEnvelope('VERSION_CONFLICT', 409),
        },
      ],
    );
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T004'));
    fireEvent.click(screen.getByTestId('task-form-submit'));

    expect(
      await screen.findByText(
        'Someone else updated this first. Reload to get the latest version, then retry.',
      ),
    ).toBeTruthy();
    expect(screen.getByTestId('task-form-modal')).toBeTruthy();
  });

  it('is keyboard-operable: focus lands in the dialog and Escape prompts before discarding', async () => {
    boardWith([]);
    renderWithQueryClient(<Board pid={PID} />);
    await openCreateModal();

    // Section 13.4: the dialog takes focus on open (Radix focus management).
    await waitFor(() => {
      expect(screen.getByTestId('task-form-modal').contains(document.activeElement)).toBe(true);
    });

    // Clean modal: Escape closes without ceremony.
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());

    // Dirty modal: Escape asks before discarding unsaved changes.
    await openCreateModal();
    fireEvent.change(within(screen.getByTestId('task-form-modal')).getByLabelText('Title'), {
      target: { value: 'Unsaved work' },
    });
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.getByTestId('task-form-discard-confirm')).toBeTruthy();
    fireEvent.click(screen.getByTestId('task-form-discard-confirm-cancel'));
    expect(screen.getByTestId('task-form-modal')).toBeTruthy();

    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.click(screen.getByTestId('task-form-discard-confirm-yes'));
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());
  });
});
