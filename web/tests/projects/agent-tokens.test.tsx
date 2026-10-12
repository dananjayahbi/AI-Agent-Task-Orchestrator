/**
 * MT-4.2-04 — agent token UI: one-time reveal with no persistence, metadata
 * only in the list, confirmation-gated revocation with list refresh, and
 * canonical error mapping (Sections 9.2, 12.2, 12.4).
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TokenSection } from '@/components/projects/token-section';
import { setUnauthorizedHandler } from '@/lib/api/client';
import { errorResponse, installApi, jsonResponse, renderWithQueryClient } from '../helpers/api';

const PLAINTEXT = 'aot-plaintext-token-value-1234567890'; // pragma: allowlist secret

function makeToken(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 11,
    kind: 'agent',
    project_id: 'PID00001',
    scopes: ['coder'],
    expires_at: null,
    revoked_at: null,
    last_used_at: '2026-10-10T00:00:00Z',
    ...overrides,
  };
}

function setClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
}

beforeEach(() => {
  setUnauthorizedHandler(null);
  window.localStorage.clear();
  window.sessionStorage.clear();
  setClipboard(vi.fn().mockResolvedValue(undefined));
});

afterEach(() => {
  setUnauthorizedHandler(null);
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('TokenSection', () => {
  it('lists non-secret metadata only — never a token value', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tokens\?/,
        respond: () => jsonResponse({ results: [makeToken()], next_cursor: null }),
      },
    ]);
    renderWithQueryClient(<TokenSection pid="PID00001" />);

    await waitFor(() => expect(screen.getByText('Token #11 · coder')).toBeTruthy());
    expect(screen.getByText(/Active · last used/)).toBeTruthy();
    expect(screen.queryByTestId('token-value')).toBeNull();
    expect(screen.queryByText(PLAINTEXT)).toBeNull();
  });

  it('creates a token, reveals the value exactly once with storage guidance', async () => {
    const { calls } = installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tokens\?/,
        respond: () => jsonResponse({ results: [makeToken()], next_cursor: null }),
      },
      {
        method: 'POST',
        match: /\/api\/v1\/tokens\/agent$/,
        respond: () => jsonResponse(makeToken({ token: PLAINTEXT, id: 12 }), 201),
      },
    ]);

    renderWithQueryClient(<TokenSection pid="PID00001" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Create agent token' }));

    await waitFor(() => expect(screen.getByTestId('token-value').textContent).toBe(PLAINTEXT));
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({
      project_id: 'PID00001',
    });

    // One-time warning + storage pointer (Section 12.2 / 10.3 step 3).
    expect(screen.getByText(/only time the token will be shown/)).toBeTruthy();
    expect(screen.getByText(/user-level agent configuration or environment/)).toBeTruthy();

    // Copy hands over the value.
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    fireEvent.click(screen.getByRole('button', { name: 'Copy token' }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(PLAINTEXT));
    expect(screen.getByText('Token copied to clipboard.')).toBeTruthy();

    // No secret in any storage artifact (Section 12.4).
    expect(JSON.stringify(window.localStorage)).not.toContain(PLAINTEXT);
    expect(JSON.stringify(window.sessionStorage)).not.toContain(PLAINTEXT);
  });

  it('discards the revealed value on unmount/navigation — nothing persists', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tokens\?/,
        respond: () => jsonResponse({ results: [], next_cursor: null }),
      },
      {
        method: 'POST',
        match: /\/api\/v1\/tokens\/agent$/,
        respond: () => jsonResponse(makeToken({ token: PLAINTEXT, id: 12 }), 201),
      },
    ]);

    const { unmount } = renderWithQueryClient(<TokenSection pid="PID00001" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Create agent token' }));
    await waitFor(() => expect(screen.getByTestId('token-value').textContent).toBe(PLAINTEXT));

    unmount();

    expect(JSON.stringify(window.localStorage)).not.toContain(PLAINTEXT);
    expect(JSON.stringify(window.sessionStorage)).not.toContain(PLAINTEXT);

    // Remount → fresh state: the reveal is gone for good.
    const second = renderWithQueryClient(<TokenSection pid="PID00001" />);
    await screen.findByRole('button', { name: 'Create agent token' });
    expect(second.queryByTestId('token-value')).toBeNull();
  });

  it('gates revocation behind confirmation, calls DELETE and refreshes the list', async () => {
    let revoked = false;
    const { calls, queryClient } = (function () {
      const installed = installApi([
        {
          method: 'GET',
          match: /\/api\/v1\/tokens\?/,
          respond: () => jsonResponse({ results: revoked ? [] : [makeToken()], next_cursor: null }),
        },
        {
          method: 'DELETE',
          match: /\/api\/v1\/tokens\/11$/,
          respond: () => {
            revoked = true;
            return jsonResponse({ revoked_at: '2026-10-12T09:00:00Z' });
          },
        },
      ]);
      const rendered = renderWithQueryClient(<TokenSection pid="PID00001" />);
      return { ...installed, ...rendered };
    })();
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries');

    await waitFor(() => expect(screen.getByText('Token #11 · coder')).toBeTruthy());
    fireEvent.click(screen.getByRole('button', { name: 'Revoke' }));

    const dialog = await screen.findByRole('dialog');
    expect(dialog.textContent).toContain('lose access immediately');
    expect(calls.filter((call) => call.method === 'DELETE')).toHaveLength(0);

    fireEvent.click(screen.getByRole('button', { name: 'Revoke token' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(calls.find((call) => call.method === 'DELETE')?.pathname).toBe('/api/v1/tokens/11');
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['projects', 'PID00001', 'tokens'] });
    // List refreshed → the revoked row is gone.
    await waitFor(() => expect(screen.queryByText('Token #11 · coder')).toBeNull());
    expect(screen.getByText('Token revoked.')).toBeTruthy();
  });

  it('maps creation failures to friendly copy and never reveals a value', async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tokens\?/,
        respond: () => jsonResponse({ results: [], next_cursor: null }),
      },
      {
        method: 'POST',
        match: /\/api\/v1\/tokens\/agent$/,
        respond: () => errorResponse('AUTH_REQUIRED', 401),
      },
    ]);

    renderWithQueryClient(<TokenSection pid="PID00001" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Create agent token' }));

    await waitFor(() => expect(handler).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText(/Sign-in is required/)).toBeTruthy());
    expect(screen.queryByTestId('token-reveal')).toBeNull();
  });

  it('shows friendly copy when the token list fails', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tokens\?/,
        respond: () => errorResponse('SERVER_ERROR', 500, 'raw stack'),
      },
    ]);

    renderWithQueryClient(<TokenSection pid="PID00001" />);

    await waitFor(() =>
      expect(
        screen.getByText(
          'The server had a problem handling this request. Try again — if it keeps failing, share the reference ID with support.',
        ),
      ).toBeTruthy(),
    );
    expect(screen.queryByText('raw stack')).toBeNull();
  });
});
