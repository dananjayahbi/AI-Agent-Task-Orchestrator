/**
 * MT-4.2-02 — project forms: create with server-assigned PID + list
 * invalidation, edit with VERSION_CONFLICT rollback to server truth,
 * confirmation-gated status transitions with friendly rejection copy,
 * policy editor showing server values and saving changed fields only, and
 * verbatim rules round-trip (Section 10.6 consumer expectation).
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { CreateProjectForm } from '@/components/projects/create-project-form';
import { EditProjectForm } from '@/components/projects/edit-project-form';
import { PolicyForm } from '@/components/projects/policy-form';
import { ProjectStatusActions } from '@/components/projects/project-status-actions';
import { ProjectSettings } from '@/components/projects/project-settings';
import { RulesForm } from '@/components/projects/rules-form';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makePolicy,
  makeProject,
  renderWithQueryClient,
} from '../helpers/api';

const VERSION_CONFLICT_COPY =
  'Someone else updated this first. Reload to get the latest version, then retry.';

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('CreateProjectForm', () => {
  it('creates via POST /projects, shows the backend-assigned PID and invalidates the list', async () => {
    const { calls } = installApi([
      {
        method: 'POST',
        match: /\/api\/v1\/projects$/,
        respond: () => jsonResponse(makeProject({ id: 'PID00007' }), 201),
      },
    ]);
    const { queryClient } = renderWithQueryClient(<CreateProjectForm />);
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries');

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Tea Factory ERP' } });
    fireEvent.change(screen.getByLabelText('Repository path'), {
      target: { value: '/srv/repos/tea' },
    });
    fireEvent.change(screen.getByLabelText('Default branch'), { target: { value: 'main' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create project' }));

    await waitFor(() => expect(screen.getByTestId('created-pid').textContent).toBe('PID00007'));

    expect(calls).toHaveLength(1);
    expect(calls[0]?.body).toEqual({
      name: 'Tea Factory ERP',
      repo_path: '/srv/repos/tea',
      default_branch: 'main',
      system_prompt_rules: '',
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects'] });
    expect(screen.getByRole('link', { name: 'Continue to project settings' })).toBeTruthy();
  });

  it('validates required fields locally and never posts an invalid payload', async () => {
    const { calls } = installApi([]);
    renderWithQueryClient(<CreateProjectForm />);

    fireEvent.click(screen.getByRole('button', { name: 'Create project' }));

    expect((await screen.findAllByText('This field is required.')).length).toBeGreaterThan(0);
    expect(calls).toHaveLength(0);
  });
});

describe('EditProjectForm', () => {
  it('PATCHes only the changed fields and confirms the save', async () => {
    const project = makeProject();
    const { calls } = installApi([
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001$/,
        respond: () => jsonResponse(project),
      },
    ]);
    renderWithQueryClient(<EditProjectForm pid="PID00001" project={project as never} />);

    expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('Tea Factory ERP');
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Tea Factory ERP v2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => expect(screen.getByText('Changes saved.')).toBeTruthy());
    expect(calls[0]?.body).toEqual({ name: 'Tea Factory ERP v2' });
  });

  it('rolls back to server truth with friendly copy on VERSION_CONFLICT', async () => {
    let projectFetches = 0;
    const freshName = () => (projectFetches++ === 0 ? 'Original' : 'Server Wins');
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001(\?|$)/,
        respond: () => jsonResponse(makeProject({ name: freshName() })),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy$/,
        respond: () => jsonResponse(makePolicy()),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/manifest$/,
        respond: () =>
          new Response('{"schema_version":1}', {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          }),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/tokens\?/,
        respond: () => jsonResponse({ results: [], next_cursor: null }),
      },
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001$/,
        respond: () => errorResponse('VERSION_CONFLICT', 409),
      },
    ]);
    renderWithQueryClient(<ProjectSettings pid="PID00001" />);

    const nameInput = (await screen.findByLabelText('Name')) as HTMLInputElement;
    await waitFor(() => expect(nameInput.value).toBe('Original'));

    fireEvent.change(nameInput, { target: { value: 'Edited by me' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() => expect(screen.getByText(VERSION_CONFLICT_COPY)).toBeTruthy());
    // Server truth wins: the invalidated refetch flows back into the form.
    await waitFor(() =>
      expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('Server Wins'),
    );
    expect(calls.some((call) => call.method === 'PATCH')).toBe(true);
  });
});

describe('ProjectStatusActions', () => {
  const active = () => makeProject({ active_status: 'active' });

  it('offers only the transitions the server permits for the current status', () => {
    renderWithQueryClient(
      <ProjectStatusActions project={makeProject({ active_status: 'archived' }) as never} />,
    );

    expect(screen.getByRole('button', { name: 'Restore' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Pause' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Archive' })).toBeNull();
  });

  it('gates the transition behind a confirmation dialog', async () => {
    const { calls } = installApi([
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001$/,
        respond: () => jsonResponse(makeProject({ active_status: 'archived' })),
      },
    ]);
    const { queryClient } = renderWithQueryClient(
      <ProjectStatusActions project={active() as never} />,
    );
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries');

    fireEvent.click(screen.getByRole('button', { name: 'Archive' }));
    expect(await screen.findByRole('dialog')).toBeTruthy();
    expect(screen.getByText('Archive this project?')).toBeTruthy();
    // Nothing sent until confirmed.
    expect(calls).toHaveLength(0);

    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(calls[0]?.body).toEqual({ active_status: 'archived' });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects', 'PID00001'] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects'] });
  });

  it('keeps the dialog open with friendly copy when the server rejects', async () => {
    const { calls } = installApi([
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001$/,
        respond: () => errorResponse('VALIDATION_ERROR', 400),
      },
    ]);
    renderWithQueryClient(<ProjectStatusActions project={active() as never} />);

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Confirm' }));

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toContain(
        "Some of the information you provided isn't valid.",
      ),
    );
    expect(screen.getByRole('dialog')).toBeTruthy();
    expect(calls).toHaveLength(1);
  });
});

describe('PolicyForm', () => {
  it('shows current server values — never client-invented defaults', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy$/,
        respond: () =>
          jsonResponse(makePolicy({ lease_duration_minutes: 77, branch_prefix: 'team/{PID}-' })),
      },
    ]);

    renderWithQueryClient(<PolicyForm pid="PID00001" />);

    const lease = (await screen.findByLabelText('Lease duration (minutes)')) as HTMLInputElement;
    await waitFor(() => expect(lease.value).toBe('77'));
    expect((screen.getByLabelText('Branch prefix') as HTMLInputElement).value).toBe('team/{PID}-');
  });

  it('saves only the changed fields through PATCH /policy', async () => {
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy$/,
        respond: () => jsonResponse(makePolicy()),
      },
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001\/policy$/,
        respond: () => jsonResponse(makePolicy({ max_retries: 5 })),
      },
    ]);
    renderWithQueryClient(<PolicyForm pid="PID00001" />);

    const retries = (await screen.findByLabelText('Max retries')) as HTMLInputElement;
    await waitFor(() => expect(retries.value).toBe('3'));

    fireEvent.change(retries, { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));

    await waitFor(() =>
      expect(screen.getByText('Policy saved. It applies from the next claim.')).toBeTruthy(),
    );
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(1);
    expect(calls.find((call) => call.method === 'PATCH')?.body).toEqual({ max_retries: 5 });
  });

  it('rejects out-of-contract values with field errors before any request', async () => {
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/policy$/,
        respond: () => jsonResponse(makePolicy()),
      },
    ]);
    renderWithQueryClient(<PolicyForm pid="PID00001" />);

    const confidence = (await screen.findByLabelText(
      'Auditor min confidence (1–5)',
    )) as HTMLInputElement;
    await waitFor(() => expect(confidence.value).toBe('4'));

    fireEvent.change(confidence, { target: { value: '9' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));

    expect(await screen.findByText('Enter a confidence between 1 and 5.')).toBeTruthy();
    expect(calls.filter((call) => call.method === 'PATCH')).toHaveLength(0);
  });
});

describe('RulesForm', () => {
  const VERBATIM = '  # Project rules\nkeep   inner spacing\n\ntrailing spaces here  \n';

  it('round-trips system_prompt_rules verbatim — no trimming, no reformatting', async () => {
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001(\?|$)/,
        respond: () => jsonResponse(makeProject({ system_prompt_rules: VERBATIM })),
      },
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001$/,
        respond: () =>
          jsonResponse(makeProject({ system_prompt_rules: `${VERBATIM}- added rule\n` })),
      },
    ]);
    renderWithQueryClient(<RulesForm pid="PID00001" />);

    const editor = (await screen.findByLabelText('Agent rules (markdown)')) as HTMLTextAreaElement;
    await waitFor(() => expect(editor.value).toBe(VERBATIM));
    // Untouched → nothing to save.
    expect((screen.getByRole('button', { name: 'Save rules' }) as HTMLButtonElement).disabled).toBe(
      true,
    );

    const next = `${VERBATIM}- added rule  `;
    fireEvent.change(editor, { target: { value: next } });
    fireEvent.click(screen.getByRole('button', { name: 'Save rules' }));

    await waitFor(() => expect(screen.getByText('Rules saved.')).toBeTruthy());
    expect(calls.find((call) => call.method === 'PATCH')?.body).toEqual({
      system_prompt_rules: next,
    });
  });

  it('surfaces friendly copy when the server rejects the rules update', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001(\?|$)/,
        respond: () => jsonResponse(makeProject({ system_prompt_rules: 'base' })),
      },
      {
        method: 'PATCH',
        match: /\/api\/v1\/projects\/PID00001$/,
        respond: () => errorResponse('SERVER_ERROR', 500, 'boom raw'),
      },
    ]);
    renderWithQueryClient(<RulesForm pid="PID00001" />);

    const editor = (await screen.findByLabelText('Agent rules (markdown)')) as HTMLTextAreaElement;
    await waitFor(() => expect(editor.value).toBe('base'));

    fireEvent.change(editor, { target: { value: 'base\nchanged' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save rules' }));

    await waitFor(() =>
      expect(screen.getByRole('alert').textContent).toContain(
        'The server had a problem handling this request.',
      ),
    );
    expect(screen.queryByText('boom raw')).toBeNull();
  });
});
