/**
 * MT-4.2-01 — project list and switcher: render from `GET /projects` through
 * the generated client, cursor paging, loading/empty/error states with
 * catalog copy, AUTH_REQUIRED redirect behaviour, and the switcher's
 * route-as-source-of-truth + persistence rules.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ProjectList } from '@/components/projects/project-list';
import {
  CURRENT_PROJECT_STORAGE_KEY,
  ProjectSwitcher,
} from '@/components/projects/project-switcher';
import { setUnauthorizedHandler } from '@/lib/api/client';
import {
  renderWithQueryClient,
  errorResponse,
  installApi,
  jsonResponse,
  makeProject,
  pageOf,
} from '../helpers/api';

const pushMock = vi.hoisted(() => vi.fn());
const pathnameHolder = vi.hoisted(() => ({ value: '/' }));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn(), refresh: vi.fn() }),
  usePathname: () => pathnameHolder.value,
}));

beforeEach(() => {
  pushMock.mockReset();
  pathnameHolder.value = '/';
  window.localStorage.clear();
  setUnauthorizedHandler(null);
});

afterEach(() => {
  setUnauthorizedHandler(null);
  vi.unstubAllGlobals();
});

describe('ProjectList', () => {
  it('renders id, name and status for every project from GET /projects', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () =>
          jsonResponse(
            pageOf([
              makeProject(),
              makeProject({ id: 'PID00002', name: 'Billing Service', active_status: 'paused' }),
            ]),
          ),
      },
    ]);

    renderWithQueryClient(<ProjectList />);

    await waitFor(() => expect(screen.getByText('Tea Factory ERP')).toBeTruthy());
    expect(screen.getByText('PID00001')).toBeTruthy();
    expect(screen.getByText('active')).toBeTruthy();
    expect(screen.getByText('Billing Service')).toBeTruthy();
    expect(screen.getByText('paused')).toBeTruthy();
    expect(screen.getByText('PID00002')).toBeTruthy();
  });

  it('shows a loading state while the list is pending', async () => {
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: async () => {
          await gate;
          return jsonResponse(pageOf([makeProject()]));
        },
      },
    ]);

    renderWithQueryClient(<ProjectList />);
    expect(screen.getByText('Loading projects…')).toBeTruthy();

    release?.();
    await waitFor(() => expect(screen.getByText('Tea Factory ERP')).toBeTruthy());
  });

  it('shows the empty state with a create call-to-action (MT-4.2-02 entry point)', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
    ]);

    renderWithQueryClient(<ProjectList />);

    await waitFor(() => expect(screen.getByText('No projects yet')).toBeTruthy());
    const cta = screen.getByRole('link', { name: 'Create a project' });
    expect(cta.getAttribute('href')).toBe('/projects/new');
  });

  it('maps backend failures to catalog copy and never shows the raw message', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () => errorResponse('SERVER_ERROR', 500, 'Traceback: very raw detail'),
      },
    ]);

    renderWithQueryClient(<ProjectList />);

    await waitFor(() =>
      expect(
        screen.getByText(
          'The server had a problem handling this request. Try again — if it keeps failing, share the reference ID with support.',
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText('Traceback: very raw detail')).toBeNull();
    expect(screen.getByText('Reference ID: corr-test')).toBeTruthy();
  });

  it('fires the silent login redirect for a mid-session AUTH_REQUIRED (WP-4.1 behaviour)', async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () => errorResponse('AUTH_REQUIRED', 401),
      },
    ]);

    renderWithQueryClient(<ProjectList />);

    await waitFor(() => expect(handler).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText('Sign-in required')).toBeTruthy());
  });

  it('honors cursor pagination — every page is requested and rendered', async () => {
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\?/,
        respond: ({ search }) => {
          const cursor = new URLSearchParams(search).get('cursor');
          if (cursor === null) {
            return jsonResponse(pageOf([makeProject()], 'cursor-page-2'));
          }
          expect(cursor).toBe('cursor-page-2');
          return jsonResponse(pageOf([makeProject({ id: 'PID00009', name: 'Second Page' })]));
        },
      },
    ]);

    renderWithQueryClient(<ProjectList />);

    await waitFor(() => expect(screen.getByText('Tea Factory ERP')).toBeTruthy());
    await waitFor(() => expect(screen.getByText('Second Page')).toBeTruthy());

    const projectCalls = calls.filter((call) => call.pathname === '/api/v1/projects');
    expect(projectCalls).toHaveLength(2);
    expect(projectCalls[1].search).toContain('cursor=cursor-page-2');
    expect(projectCalls[0].search).toContain('page_size=100');
  });
});

describe('ProjectSwitcher', () => {
  function installProjects() {
    return installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () =>
          jsonResponse(
            pageOf([makeProject(), makeProject({ id: 'PID00002', name: 'Billing Service' })]),
          ),
      },
    ]);
  }

  it('takes the current project from the route — the source of truth', async () => {
    window.localStorage.setItem(CURRENT_PROJECT_STORAGE_KEY, 'PID00002');
    pathnameHolder.value = '/projects/PID00001/board';
    installProjects();

    renderWithQueryClient(<ProjectSwitcher />);

    const select = (await screen.findByTestId('project-switcher')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('PID00001'));
    // …and the route selection re-syncs the stored value.
    expect(window.localStorage.getItem(CURRENT_PROJECT_STORAGE_KEY)).toBe('PID00001');
  });

  it('changes the current project and navigates to its board, persisting the selection', async () => {
    installProjects();

    renderWithQueryClient(<ProjectSwitcher />);

    const select = (await screen.findByTestId('project-switcher')) as HTMLSelectElement;
    // No route context, no stored value → first project preselects.
    await waitFor(() => expect(select.value).toBe('PID00001'));

    fireEvent.change(select, { target: { value: 'PID00002' } });

    expect(pushMock).toHaveBeenCalledWith('/projects/PID00002/board');
    expect(window.localStorage.getItem(CURRENT_PROJECT_STORAGE_KEY)).toBe('PID00002');
  });

  it('restores the stored selection across reloads on pages without a project route', async () => {
    window.localStorage.setItem(CURRENT_PROJECT_STORAGE_KEY, 'PID00002');
    pathnameHolder.value = '/review';
    installProjects();

    renderWithQueryClient(<ProjectSwitcher />);

    const select = (await screen.findByTestId('project-switcher')) as HTMLSelectElement;
    await waitFor(() => expect(select.value).toBe('PID00002'));
  });

  it('stays out of the way while the list loads or fails (pages own those states)', () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects(\?|$)/,
        respond: () => new Promise<Response>(() => undefined),
      },
    ]);
    const { container } = renderWithQueryClient(<ProjectSwitcher />);
    expect(container.firstChild).toBeNull();
  });
});
