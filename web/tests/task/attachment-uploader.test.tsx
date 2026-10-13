/**
 * MT-4.5-05 — attachment uploader: drop/picker upload with per-file
 * progress, processing status driven exclusively by `attachment.*`
 * stream events (no polling), Section 9.5 client pre-checks with
 * canonical server rejections, failed-reason display, removal via
 * DELETE, and the create-mode upload sequence (no phantom uploads).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  tasksServerRoute,
} from '../helpers/api';
import type { Route } from '../helpers/api';

const PID = 'PID00001';

beforeEach(() => {
  vi.unstubAllGlobals();
});

function makeAttachment(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'att-1',
    task_id: 'PID00001-T030',
    filename: 'spec.md',
    mime_type: 'text/markdown',
    size: 1024,
    is_image: false,
    processing_status: 'uploaded',
    failure_reason: null,
    token_count: null,
    ...overrides,
  };
}

type Harness = {
  calls: ReturnType<typeof installApi>['calls'];
  emit: (envelope: unknown) => void;
};

function boardHarness(options: {
  tasks: unknown[];
  attachments?: unknown[];
  extraRoutes?: Route[];
  uploadResponse?: (file: File | undefined, callIndex: number) => Response | Promise<Response>;
  createResponse?: () => Response | Promise<Response>;
}): Harness {
  const attachments = options.attachments ?? [];
  const stream = sseConnection();
  let uploadCalls = 0;
  const routes: Route[] = [
    tasksServerRoute(PID, options.tasks),
    {
      method: 'GET',
      match: new RegExp(`/api/v1/projects/${PID}/policy(\\?|$)`),
      respond: () => jsonResponse(makePolicy()),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => stream.response,
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/PID00001-T030\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf(attachments)),
    },
    {
      method: 'POST',
      match: /\/api\/v1\/tasks\/PID00001-T030\/attachments$/,
      respond: () => {
        const index = uploadCalls++;
        return options.uploadResponse?.(undefined, index) ?? jsonResponse(makeAttachment(), 201);
      },
    },
    {
      method: 'DELETE',
      match: /\/api\/v1\/attachments\/att-1$/,
      respond: () => new Response(null, { status: 204 }),
    },
    ...(options.createResponse === undefined
      ? []
      : [
          {
            method: 'POST',
            match: new RegExp(`/api/v1/projects/${PID}/tasks$`),
            respond: () => options.createResponse!(),
          },
        ]),
    ...(options.extraRoutes ?? []),
  ];
  const { calls } = installApi(routes);
  return {
    calls,
    emit: (envelope) => stream.frame(Math.floor(Math.random() * 1_000_000) + 1, envelope),
  };
}

const EDIT_TASK = () => makeTask({ id: 'PID00001-T030', state: 'draft', title: 'Attach things' });

async function openEditorForTask(task: { id: string }) {
  fireEvent.click(await screen.findByLabelText(`Edit task ${task.id}`));
  await waitFor(() => expect(screen.getByTestId('task-form-modal')).toBeTruthy());
}

function attachFile(name: string, type: string, size: number) {
  const file = new File(['x'.repeat(size)], name, { type });
  const input = screen.getByTestId('dropzone-input') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [file] } });
  return file;
}

describe('attachment-uploader', () => {
  it('uploads via the multipart endpoint with visible per-file progress and shows the server row', async () => {
    const release: { upload: ((response: Response) => void) | null } = { upload: null };
    const harness = boardHarness({
      tasks: [EDIT_TASK()],
      uploadResponse: () =>
        new Promise<Response>((resolve) => {
          release.upload = resolve;
        }),
    });
    renderWithQueryClient(<Board pid={PID} />);
    await openEditorForTask(EDIT_TASK());

    attachFile('plan.md', 'text/markdown', 100);
    // Progress row appears while the request is in flight.
    const progress = await screen.findByRole('progressbar', { name: 'Uploading plan.md' });
    expect(progress).toBeTruthy();
    expect(screen.getByText('Uploading…')).toBeTruthy();

    // The generated client builds the request asynchronously — wait for
    // the upload call to actually land before releasing its response.
    await waitFor(() => expect(release.upload).not.toBeNull());
    release.upload?.(jsonResponse(makeAttachment({ id: 'att-9', filename: 'plan.md' }), 201));
    await waitFor(() =>
      expect(screen.getByTestId('attachment-status-att-9').textContent).toBe('Uploaded'),
    );

    const upload = harness.calls.find(
      (call) => call.method === 'POST' && call.pathname.endsWith('/attachments'),
    );
    expect(upload).toBeTruthy();
  });

  it('updates processing status only from attachment.* stream events — never polling', async () => {
    const harness = boardHarness({
      tasks: [EDIT_TASK()],
      attachments: [makeAttachment({ id: 'att-live', processing_status: 'uploaded' })],
    });
    renderWithQueryClient(<Board pid={PID} />);
    await openEditorForTask(EDIT_TASK());

    await waitFor(() =>
      expect(screen.getByTestId('attachment-status-att-live').textContent).toBe('Uploaded'),
    );
    const listCalls = () =>
      harness.calls.filter(
        (call) => call.method === 'GET' && call.pathname.endsWith('/attachments'),
      ).length;
    expect(listCalls()).toBe(1);

    // No status change without an event — advance real time, still Uploaded.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.getByTestId('attachment-status-att-live').textContent).toBe('Uploaded');
    expect(listCalls()).toBe(1); // still exactly one load: no polling loop

    harness.emit(
      makeEventEnvelope({
        type: 'attachment.processing',
        task_id: 'PID00001-T030',
        data: { attachment_id: 'att-live' },
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('attachment-status-att-live').textContent).toBe('Processing…'),
    );

    harness.emit(
      makeEventEnvelope({
        type: 'attachment.failed',
        task_id: 'PID00001-T030',
        data: { attachment_id: 'att-live', reason: 'OCR engine timed out on every page.' },
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('attachment-status-att-live').textContent).toBe('Failed'),
    );
    // FR-ATT-07: the pipeline's human-readable reason stays visible.
    expect(screen.getByTestId('attachment-failure-att-live').textContent).toBe(
      'OCR engine timed out on every page.',
    );
    // Still exactly one list load after every transition — status moved
    // purely through the stream (WP-4.5 deliverable).
    expect(listCalls()).toBe(1);
  });

  it('applies ready events and keeps failed rows removable via DELETE', async () => {
    const harness = boardHarness({
      tasks: [EDIT_TASK()],
      attachments: [
        makeAttachment({ id: 'att-ok', filename: 'a.png', processing_status: 'processing' }),
        makeAttachment({
          id: 'att-bad',
          filename: 'b.pdf',
          processing_status: 'failed',
          failure_reason: 'Encrypted PDF without a text layer.',
        }),
      ],
    });
    renderWithQueryClient(<Board pid={PID} />);
    await openEditorForTask(EDIT_TASK());

    await waitFor(() =>
      expect(screen.getByTestId('attachment-status-att-ok').textContent).toBe('Processing…'),
    );
    harness.emit(
      makeEventEnvelope({
        type: 'attachment.ready',
        task_id: 'PID00001-T030',
        data: { attachment_id: 'att-ok', token_count: 512, page_count: 3 },
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('attachment-status-att-ok').textContent).toBe('Ready'),
    );
    expect(screen.getByTestId('attachment-failure-att-bad').textContent).toBe(
      'Encrypted PDF without a text layer.',
    );

    fireEvent.click(screen.getByTestId('attachment-remove-att-bad'));
    await waitFor(() =>
      expect(
        harness.calls.some(
          (call) => call.method === 'DELETE' && call.pathname.endsWith('/att-bad'),
        ),
      ).toBe(true),
    );
  });

  it('pre-checks Section 9.5 limits client-side and maps server rejections to canonical copy', async () => {
    const harness = boardHarness({
      tasks: [EDIT_TASK()],
      attachments: [makeAttachment({ id: 'att-big', size: 26 * 1024 * 1024 })],
      uploadResponse: () => errorResponse('ATTACHMENT_UNSUPPORTED_FORMAT', 415),
    });
    renderWithQueryClient(<Board pid={PID} />);
    await openEditorForTask(EDIT_TASK());

    // Oversize: instant client rejection, no upload call.
    attachFile('huge.png', 'image/png', 26 * 1024 * 1024);
    expect(
      await screen.findByText(/The file is 26\.0 MB — the per-file limit is 25\.0 MB\./),
    ).toBeTruthy();
    expect(
      harness.calls.filter(
        (call) => call.method === 'POST' && call.pathname.endsWith('/attachments'),
      ),
    ).toHaveLength(0);

    // Disallowed type: instant client rejection.
    attachFile('movie.mp4', 'video/mp4', 100);
    expect(await screen.findByText(/aren't supported — accepted/)).toBeTruthy();

    // A type the browser cannot classify passes to the server, which
    // rejects it — the catalog message lands, per file.
    attachFile('weird.bin', '', 100);
    await waitFor(() =>
      expect(
        screen.getByText(
          /That file type isn't supported\. Upload one of the accepted formats instead\./,
        ),
      ).toBeTruthy(),
    );
  });

  it('blocks the 10-per-task cap client-side', async () => {
    boardHarness({
      tasks: [EDIT_TASK()],
      attachments: Array.from({ length: 10 }, (_, i) =>
        makeAttachment({ id: `att-${i}`, filename: `f${i}.txt` }),
      ),
    });
    renderWithQueryClient(<Board pid={PID} />);
    await openEditorForTask(EDIT_TASK());
    // Wait for the 10 existing rows to load — the cap check counts them.
    await waitFor(() => expect(screen.getAllByRole('listitem', { name: '' })).toBeTruthy());
    await waitFor(() =>
      expect(document.querySelectorAll('[data-testid^="attachment-row-"]').length).toBe(10),
    );

    attachFile('one-more.txt', 'text/plain', 10);
    expect(
      await screen.findByText(/This task already has the maximum of 10 attachments/),
    ).toBeTruthy();
  });

  it('queues create-mode uploads and sends nothing until the draft exists (cancel path clean)', async () => {
    const tasks: unknown[] = [];
    const release = { create: null as ((response: Response) => void) | null };
    const harness = boardHarness({
      tasks,
      createResponse: () =>
        new Promise<Response>((resolve) => {
          release.create = resolve;
        }),
    });
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByTestId('board-new-task'));
    attachFile('queued.md', 'text/markdown', 50);
    expect(screen.getByText('Waiting for draft…')).toBeTruthy();
    // Nothing left the browser: the create is still pending.
    expect(
      harness.calls.filter(
        (call) => call.method === 'POST' && call.pathname.endsWith('/attachments'),
      ),
    ).toHaveLength(0);

    // Submit the create, then cancel while it is still in flight — the
    // modal unmounts, so the queued file has nothing to flush into.
    fireEvent.change(within(screen.getByTestId('task-form-modal')).getByLabelText('Title'), {
      target: { value: 'Queued upload task' },
    });
    fireEvent.click(screen.getByTestId('task-form-submit'));
    fireEvent.keyDown(document, { key: 'Escape' });
    fireEvent.click(screen.getByTestId('task-form-discard-confirm-yes'));
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());
    // Wait for the in-flight create to land, then resolve it — the modal
    // is already gone, so the queued file must not flush.
    await waitFor(() =>
      expect(
        harness.calls.some((call) => call.method === 'POST' && call.pathname.endsWith('/tasks')),
      ).toBe(true),
    );
    release.create?.(jsonResponse(makeTask({ id: 'PID00001-T099', state: 'draft' }), 201));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(
      harness.calls.filter(
        (call) => call.method === 'POST' && call.pathname.endsWith('/attachments'),
      ),
    ).toHaveLength(0);
    // The cancelled close stays closed even though the create resolved.
    expect(screen.queryByTestId('task-form-modal')).toBeNull();
  });
});
