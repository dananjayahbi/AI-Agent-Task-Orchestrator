import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { LoginForm } from '@/components/login/login-form';

const replaceMock = vi.hoisted(() => vi.fn());
const refreshMock = vi.hoisted(() => vi.fn());

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: replaceMock, refresh: refreshMock }),
}));

const fetchMock = vi.fn();

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function fillAndSubmit() {
  fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'owner' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'pw' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  replaceMock.mockReset();
  refreshMock.mockReset();
  window.localStorage.clear();
});

describe('LoginForm', () => {
  it('signs in and resumes at the return path (login happy path)', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        token: 'PLAINTEXT-BINDING-NEVER-STORED',
        expires_at: '2026-10-13T09:00:00Z',
        user: { id: 7, username: 'owner' },
      }),
    );

    render(<LoginForm returnTo="/review" />);
    fillAndSubmit();

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith('/review'));
    expect(refreshMock).toHaveBeenCalled();
    expect(window.localStorage.getItem('orchestrator.web.session.user')).not.toContain(
      'PLAINTEXT-BINDING-NEVER-STORED',
    );
    expect(fetchMock.mock.calls[0]?.[0]).toBeInstanceOf(Request);
    expect(new URL((fetchMock.mock.calls[0]?.[0] as Request).url).pathname).toBe(
      '/api/v1/auth/login',
    );
  });

  it('renders friendly credential-failure copy, never the raw server message', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'AUTH_REQUIRED',
            message: 'Invalid username or password.',
            retryable: false,
            details: null,
            correlation_id: 'corr-1',
          },
        },
        401,
      ),
    );

    render(<LoginForm returnTo="/" />);
    fillAndSubmit();

    await waitFor(() => {
      expect(
        screen.getByText('Sign-in is required. Check your username and password and try again.'),
      ).toBeTruthy();
    });
    expect(screen.queryByText('Invalid username or password.')).toBeNull();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it('shows the SERVER_ERROR catalog copy for a non-JSON failure, never the raw body', async () => {
    fetchMock.mockResolvedValue(new Response('bad gateway', { status: 502 }));

    render(<LoginForm returnTo="/" />);
    fillAndSubmit();

    await waitFor(() => {
      expect(
        screen.getByText(
          'The server had a problem handling this request. Try again — if it keeps failing, share the reference ID with support.',
        ),
      ).toBeTruthy();
    });
    expect(screen.queryByText('bad gateway')).toBeNull();
  });
});
