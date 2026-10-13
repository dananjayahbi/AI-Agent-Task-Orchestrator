/**
 * MT-4.5-03 — acceptance-criteria and target-scope editors: ordered
 * add/edit/remove with save→reload fidelity; glob rules mirroring
 * WP-1.4's `validate_target_scope_globs` fixture set (Section 12.3);
 * server VALIDATION_ERROR mapped per index with the modal staying open
 * (Section 13.3); the displayed scope set matching what is saved (R2).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { validateTargetScope } from '@/lib/forms/glob-rules';
import {
  installApi,
  jsonResponse,
  makeTask,
  renderWithQueryClient,
  tasksServerRoute,
} from '../helpers/api';

const PID = 'PID00001';

beforeEach(() => {
  vi.unstubAllGlobals();
});

function envelope(code: string, status: number, details: unknown = null): Response {
  return jsonResponse(
    {
      error: { code, message: `${code}.`, retryable: false, details, correlation_id: 'c' },
    },
    status,
  );
}

describe('criteria-scope-editors', () => {
  it('manages acceptance criteria as an ordered list and round-trips through save and reload', async () => {
    const tasks: unknown[] = [
      makeTask({ id: 'PID00001-T020', state: 'draft', acceptance_criteria: [] }),
    ];
    const { calls } = installApi([
      tasksServerRoute(PID, tasks),
      {
        method: 'PATCH',
        match: /\/api\/v1\/tasks\/PID00001-T020$/,
        respond: ({ body }) => {
          const patched = body as { acceptance_criteria: string[] };
          tasks[0] = makeTask({
            id: 'PID00001-T020',
            state: 'draft',
            acceptance_criteria: patched.acceptance_criteria,
            version: 2,
          });
          return jsonResponse(tasks[0]);
        },
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T020'));
    fireEvent.click(screen.getByTestId('criteria-add'));
    fireEvent.click(screen.getByTestId('criteria-add'));
    fireEvent.change(screen.getByLabelText('Criterion 1'), {
      target: { value: '  Login accepts valid credentials  ' },
    });
    fireEvent.change(screen.getByLabelText('Criterion 2'), {
      target: { value: 'Bad password rejected' },
    });
    // Remove the second entry, then re-add — order stays user-controlled.
    fireEvent.click(screen.getByTestId('criteria-remove-1'));
    fireEvent.click(screen.getByTestId('criteria-add'));
    fireEvent.change(screen.getByLabelText('Criterion 2'), {
      target: { value: 'Session persists' },
    });

    fireEvent.click(screen.getByTestId('task-form-submit'));
    await waitFor(() => expect(screen.getByText('Changes saved.')).toBeTruthy());

    const patch = calls.find((call) => call.method === 'PATCH');
    expect(patch?.body).toMatchObject({
      acceptance_criteria: ['Login accepts valid credentials', 'Session persists'],
    });

    // Reload: fresh mount shows the identical ordered list.
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());
    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T020'));
    const modal = within(screen.getByTestId('task-form-modal'));
    expect((modal.getByLabelText('Criterion 1') as HTMLTextAreaElement).value).toBe(
      'Login accepts valid credentials',
    );
    expect((modal.getByLabelText('Criterion 2') as HTMLTextAreaElement).value).toBe(
      'Session persists',
    );
  });

  it('blocks blank criterion rows with inline feedback and never submits them', async () => {
    const task = makeTask({ id: 'PID00001-T021', state: 'draft' });
    const { calls } = installApi([tasksServerRoute(PID, [task])]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T021'));
    fireEvent.click(screen.getByTestId('criteria-add'));
    fireEvent.click(screen.getByTestId('task-form-submit'));

    expect(
      await within(screen.getByTestId('task-form-modal')).findByText(
        'Fill in this criterion or remove the row.',
      ),
    ).toBeTruthy();
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(0);
  });

  it('accepts valid globs and rejects escape-shaped ones with per-index messages (WP-1.4 mirror)', async () => {
    const task = makeTask({ id: 'PID00001-T022', state: 'draft', target_scope: [] });
    const { calls } = installApi([tasksServerRoute(PID, [task])]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T022'));
    fireEvent.click(screen.getByTestId('scope-add'));
    fireEvent.click(screen.getByTestId('scope-add'));
    fireEvent.click(screen.getByTestId('scope-add'));
    fireEvent.change(screen.getByLabelText('Scope glob 1'), { target: { value: 'src/api/**' } });
    fireEvent.change(screen.getByLabelText('Scope glob 2'), { target: { value: '../etc/passwd' } });
    fireEvent.change(screen.getByLabelText('Scope glob 3'), { target: { value: 'C:/win' } });

    fireEvent.click(screen.getByTestId('task-form-submit'));

    const modal = within(screen.getByTestId('task-form-modal'));
    expect(await modal.findByText("A '..' segment would escape the repository root.")).toBeTruthy();
    expect(
      modal.getByText('Write the glob relative to the repository root (not an absolute path).'),
    ).toBeTruthy();
    // The valid glob is shown in the current-scope mirror; invalid ones are not.
    expect(screen.getByTestId('scope-current').textContent).toContain('src/api/**');
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(0);
  });

  it('saves trimmed globs, reloads them unchanged, and mirrors the displayed scope set', async () => {
    const tasks: unknown[] = [makeTask({ id: 'PID00001-T023', state: 'draft', target_scope: [] })];
    const { calls } = installApi([
      tasksServerRoute(PID, tasks),
      {
        method: 'PATCH',
        match: /\/api\/v1\/tasks\/PID00001-T023$/,
        respond: ({ body }) => {
          const patched = body as { target_scope: string[] };
          tasks[0] = makeTask({
            id: 'PID00001-T023',
            state: 'draft',
            target_scope: patched.target_scope,
            version: 2,
          });
          return jsonResponse(tasks[0]);
        },
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T023'));
    fireEvent.click(screen.getByTestId('scope-add'));
    fireEvent.change(screen.getByLabelText('Scope glob 1'), { target: { value: '  web/**  ' } });

    fireEvent.click(screen.getByTestId('task-form-submit'));
    await waitFor(() => expect(screen.getByText('Changes saved.')).toBeTruthy());
    const patch = calls.find((call) => call.method === 'PATCH');
    expect(patch?.body).toMatchObject({ target_scope: ['web/**'] });

    // The current-scope mirror shows exactly the saved set.
    const chips = within(screen.getByTestId('scope-current')).getAllByRole('listitem');
    expect(chips.map((chip) => chip.textContent)).toEqual(['web/**']);

    // Reload fidelity through a fresh mount.
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());
    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T023'));
    expect(
      (
        within(screen.getByTestId('task-form-modal')).getByLabelText(
          'Scope glob 1',
        ) as HTMLInputElement
      ).value,
    ).toBe('web/**');
  });

  it('maps a server VALIDATION_ERROR on target_scope to per-index field feedback and stays open', async () => {
    const task = makeTask({ id: 'PID00001-T024', state: 'draft', target_scope: [] });
    const { calls } = installApi([
      tasksServerRoute(PID, [task]),
      {
        method: 'PATCH',
        match: /\/api\/v1\/tasks\/PID00001-T024$/,
        respond: () =>
          envelope('VALIDATION_ERROR', 400, { target_scope: { 0: ['must not be empty'] } }),
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T024'));
    fireEvent.click(screen.getByTestId('scope-add'));
    fireEvent.change(screen.getByLabelText('Scope glob 1'), { target: { value: 'src/**' } });
    fireEvent.click(screen.getByTestId('task-form-submit'));

    const modal = within(screen.getByTestId('task-form-modal'));
    expect(
      await modal.findAllByText('The server rejected this value. Review it and try again.'),
    ).toBeTruthy();
    expect(screen.getByTestId('task-form-modal')).toBeTruthy();
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(1);
  });

  it('pins the WP-1.4 glob mirror against a shared fixture set', () => {
    // [input, valid?] — one fixture set both sides of the wire obey
    // (backend tests/… mirror the same shapes; see MT risk note).
    const fixtures: Array<[string, boolean]> = [
      ['src/**', true],
      ['**/migrations/**', true],
      ['a/b/c.txt', true],
      ['', false],
      ['   ', false],
      ['x'.repeat(501), false],
      ['win\\path', false],
      ['/absolute', false],
      ['C:/windows', false],
      ['a/../b', false],
      ['..', false],
    ];
    for (const [glob, valid] of fixtures) {
      const result = validateTargetScope([glob]);
      const entryValid = Object.keys(result.errors).length === 0;
      expect(
        entryValid,
        `glob ${JSON.stringify(glob)} should be ${valid ? 'valid' : 'invalid'}`,
      ).toBe(valid);
      if (valid) {
        expect(result.cleaned).toEqual([glob.trim()]);
      }
    }
    // Count cap mirrors the server's "At most 64 globs."
    const many = Array.from({ length: 65 }, (_, i) => `path-${i}/**`);
    expect(validateTargetScope(many).listError).toContain('64');
  });
});
