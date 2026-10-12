import { beforeEach, describe, expect, it, vi } from 'vitest';

import { loginRequest, logoutRequest } from '@/lib/api/auth';
import { ApiError, callApi, setUnauthorizedHandler } from '@/lib/api/client';
import { listProjects } from '@/lib/api/generated/sdk.gen';
import { performSessionExpired, performSignOut } from '@/lib/session/flows';
import { readSessionUser, saveSessionUser } from '@/lib/session/store';

const fetchMock = vi.fn();

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function calledRequest(index = 0): Request {
  return fetchMock.mock.calls[index]?.[0] as Request;
}

const OWNER_SESSION = {
  token: 'PLAINTEXT-BINDING-NEVER-STORED',
  expires_at: '2026-10-13T09:00:00Z',
  user: { id: 7, username: 'owner' },
};

const AUTH_REQUIRED_NESTED = {
  error: {
    code: 'AUTH_REQUIRED',
    message: 'Authentication credentials were not provided.',
    retryable: false,
    details: null,
    correlation_id: 'corr-401',
  },
};

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  setUnauthorizedHandler(null);
  window.localStorage.clear();
  document.cookie = 'csrftoken=csrf-123; Path=/';
});

describe('loginRequest', () => {
  it('posts credentials through the generated client and returns only the identity', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OWNER_SESSION));

    const user = await loginRequest({ username: 'owner', password: 'pw' }); // pragma: allowlist secret

    expect(user).toEqual({ id: 7, username: 'owner' });
    expect(user).not.toHaveProperty('token');

    const request = calledRequest();
    expect(new URL(request.url).pathname).toBe('/api/v1/auth/login');
    expect(request.method).toBe('POST');
    expect(request.credentials).toBe('include');
    expect(await request.clone().json()).toEqual({ username: 'owner', password: 'pw' }); // pragma: allowlist secret
    expect(request.headers.get('Content-Type')).toBe('application/json');
  });

  it('never persists the bearer binding — only the non-secret identity crosses client state', async () => {
    fetchMock.mockResolvedValue(jsonResponse(OWNER_SESSION));

    saveSessionUser(await loginRequest({ username: 'owner', password: 'pw' })); // pragma: allowlist secret

    const raw = window.localStorage.getItem('orchestrator.web.session.user');
    expect(raw).not.toBeNull();
    expect(raw).not.toContain('PLAINTEXT-BINDING-NEVER-STORED');
    expect(raw).not.toContain('token');
    expect(readSessionUser()).toEqual({ id: 7, username: 'owner' });
  });
});

describe('logoutRequest', () => {
  it('revokes the session with the CSRF header duplicated from the csrftoken cookie', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ revoked_at: '2026-10-12T09:00:00Z' }));

    await logoutRequest();

    const request = calledRequest();
    expect(new URL(request.url).pathname).toBe('/api/v1/auth/logout');
    expect(request.method).toBe('POST');
    expect(request.headers.get('X-CSRFToken')).toBe('csrf-123');
    expect(request.credentials).toBe('include');
  });
});

describe('performSignOut', () => {
  it('revokes, clears local identity and lands on login', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ revoked_at: '2026-10-12T09:00:00Z' }));
    saveSessionUser({ id: 7, username: 'owner' });
    const navigator = { assign: vi.fn() };

    await performSignOut(navigator);

    expect(readSessionUser()).toBeNull();
    expect(navigator.assign).toHaveBeenCalledWith('/login');
  });

  it('still clears and redirects when the session already expired (idempotent logout)', async () => {
    fetchMock.mockResolvedValue(jsonResponse(AUTH_REQUIRED_NESTED, 401));
    saveSessionUser({ id: 7, username: 'owner' });
    const navigator = { assign: vi.fn() };

    await performSignOut(navigator);

    expect(readSessionUser()).toBeNull();
    expect(navigator.assign).toHaveBeenCalledWith('/login');
  });
});

describe('performSessionExpired (mid-session AUTH_REQUIRED)', () => {
  it('clears local identity and returns to login with the current path', () => {
    saveSessionUser({ id: 7, username: 'owner' });
    const navigator = { assign: vi.fn() };

    performSessionExpired('/projects/PID00001/board?filter=open', navigator);

    expect(readSessionUser()).toBeNull();
    expect(navigator.assign).toHaveBeenCalledWith(
      `/login?next=${encodeURIComponent('/projects/PID00001/board?filter=open')}`,
    );
  });
});

describe('callApi error handling (Section 13.2 behaviour)', () => {
  it('parses the nested Section 9.2 envelope into ApiError fields', async () => {
    fetchMock.mockResolvedValue(jsonResponse(AUTH_REQUIRED_NESTED, 401));

    const error = await callApi(listProjects()).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(401);
    expect(apiError.code).toBe('AUTH_REQUIRED');
    expect(apiError.retryable).toBe(false);
    expect(apiError.correlationId).toBe('corr-401');
  });

  it('fires the silent redirect handler for a mid-session AUTH_REQUIRED', async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetchMock.mockResolvedValue(jsonResponse(AUTH_REQUIRED_NESTED, 401));

    await expect(callApi(listProjects())).rejects.toMatchObject({ code: 'AUTH_REQUIRED' });

    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('does not fire the redirect handler for failed login credentials', async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'AUTH_REQUIRED',
            message: 'Invalid username or password.',
            retryable: false,
            details: null,
            correlation_id: 'corr-login',
          },
        },
        401,
      ),
    );

    const badCreds = { username: 'owner', password: 'bad' }; // pragma: allowlist secret
    await expect(loginRequest(badCreds)).rejects.toMatchObject({
      code: 'AUTH_REQUIRED',
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it('tolerates a flat envelope body as a legacy fallback', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          code: 'VALIDATION_ERROR',
          message: 'Malformed body.',
          retryable: false,
          details: {},
          correlation_id: 'corr-flat',
        },
        400,
      ),
    );

    await expect(callApi(listProjects())).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      correlationId: 'corr-flat',
    });
  });

  it('degrades a non-JSON failure to the canonical SERVER_ERROR code', async () => {
    fetchMock.mockResolvedValue(new Response('bad gateway', { status: 502 }));

    await expect(callApi(listProjects())).rejects.toMatchObject({
      code: 'SERVER_ERROR',
      status: 502,
      retryable: true,
    });
  });
});
