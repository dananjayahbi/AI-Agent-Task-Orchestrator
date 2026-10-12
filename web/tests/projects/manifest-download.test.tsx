/**
 * MT-4.2-03 — manifest download and copy: exact response bytes (no client
 * assembly), `orchestrator.json` file name, clipboard success + selectable
 * fallback, secret-free/init guidance copy, and canonical error mapping.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ManifestSection } from '@/components/projects/manifest-section';
import { setUnauthorizedHandler } from '@/lib/api/client';
import { errorResponse, installApi, renderWithQueryClient } from '../helpers/api';

/** Verbatim server bytes — pretty-printed, non-ASCII, exactly what we assert. */
const RAW_MANIFEST = `{
  "$schema": "https://orchestrator.local/schemas/manifest.v1.json",
  "schema_version": 1,
  "project_id": "PID00001",
  "project_name": "Tea Café ERP",
  "orchestrator_api": "http://localhost:8000/api/v1",
  "default_branch": "main",
  "auto_branch_prefix": "feat/PID00001-",
  "audit_required_default": true
}
`;

function manifestRoute() {
  return {
    method: 'GET',
    match: /\/api\/v1\/projects\/PID00001\/manifest$/,
    respond: () =>
      new Response(RAW_MANIFEST, {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
  };
}

let blobCapture: { blob: Blob | null; download: string | null } = { blob: null, download: null };

function setClipboard(writeText: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
}

beforeEach(() => {
  blobCapture = { blob: null, download: null };
  setUnauthorizedHandler(null);
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: (blob: Blob) => {
      blobCapture.blob = blob;
      return 'blob:orchestrator-json';
    },
  });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    blobCapture.download = this.download;
  });
});

afterEach(() => {
  setUnauthorizedHandler(null);
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('ManifestSection', () => {
  it('downloads a file named orchestrator.json whose bytes match the endpoint response', async () => {
    installApi([manifestRoute()]);
    renderWithQueryClient(<ManifestSection pid="PID00001" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Download orchestrator.json' }));

    expect(blobCapture.download).toBe('orchestrator.json');
    expect(blobCapture.blob).not.toBeNull();
    expect(await blobCapture.blob!.text()).toBe(RAW_MANIFEST);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:orchestrator-json');
  });

  it('copies the same manifest content with a success acknowledgement', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    installApi([manifestRoute()]);
    renderWithQueryClient(<ManifestSection pid="PID00001" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Copy to clipboard' }));

    await waitFor(() => expect(screen.getByText('Manifest copied to clipboard.')).toBeTruthy());
    expect(writeText).toHaveBeenCalledWith(RAW_MANIFEST);
  });

  it('falls back to selectable text when the clipboard API is blocked', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('blocked'));
    setClipboard(writeText);
    installApi([manifestRoute()]);
    renderWithQueryClient(<ManifestSection pid="PID00001" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Copy to clipboard' }));

    await waitFor(() =>
      expect(
        screen.getByText(
          'Copying was blocked by the browser — select the text below and copy it manually.',
        ),
      ).toBeTruthy(),
    );
    const fallback = screen.getByLabelText('Manifest text') as HTMLTextAreaElement;
    expect(fallback.value).toBe(RAW_MANIFEST);
    expect(fallback.readOnly).toBe(true);
  });

  it('states the secret-free guarantee and the download → repo root → init flow', async () => {
    installApi([manifestRoute()]);
    renderWithQueryClient(<ManifestSection pid="PID00001" />);

    await screen.findByRole('button', { name: 'Download orchestrator.json' });
    expect(screen.getByText(/contains no secrets — it is safe to commit/)).toBeTruthy();
    expect(screen.getByText(/Agent tokens are never part of it/)).toBeTruthy();
    expect(screen.getByText(/at your repository root/)).toBeTruthy();
    expect(screen.getByText('init')).toBeTruthy();
  });

  it('maps AUTH_FORBIDDEN_PROJECT to the catalog copy', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/manifest$/,
        respond: () => errorResponse('AUTH_FORBIDDEN_PROJECT', 403),
      },
    ]);
    renderWithQueryClient(<ManifestSection pid="PID00001" />);

    await waitFor(() =>
      expect(
        screen.getByText(
          "You don't have access to this project. If you think you should, ask the project owner to grant you access.",
        ),
      ).toBeTruthy(),
    );
  });

  it('fires the silent login redirect for AUTH_REQUIRED', async () => {
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID00001\/manifest$/,
        respond: () => errorResponse('AUTH_REQUIRED', 401),
      },
    ]);
    renderWithQueryClient(<ManifestSection pid="PID00001" />);

    await waitFor(() => expect(handler).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByText('Sign-in required')).toBeTruthy());
  });

  it('maps the contract project-not-found answer (VALIDATION_ERROR, no PROJECT_NOT_FOUND in catalog)', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/projects\/PID99999\/manifest$/,
        respond: () => errorResponse('VALIDATION_ERROR', 400),
      },
    ]);
    renderWithQueryClient(<ManifestSection pid="PID99999" />);

    await waitFor(() => expect(screen.getByText('Check your entries')).toBeTruthy());
    expect(screen.getByText(/isn't valid/)).toBeTruthy();
  });
});
