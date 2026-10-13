/**
 * MT-4.6-04 — attachment viewer: image preview with OCR/description tabs
 * (Section 13.2), document pages navigable via `page_number`/`total_pages`
 * (Section 9.5; WP-4.6 acceptance), all four `processing_status` values
 * with the pipeline's `failure_reason` (FR-ATT-07), the P10 untrusted
 * content treatment, catalog-only error mapping for
 * `ATTACHMENT_NOT_READY` / `ATTACHMENT_UNSUPPORTED_FORMAT`
 * (Section 20.4 item 5), and distinct loading/empty/error states.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AttachmentViewer } from '@/components/task/detail/attachment-viewer';
import { TaskDetail } from '@/components/task/detail/task-detail';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type SseConnection,
} from '../helpers/api';
import { makeAttachment, makeAttachmentContent } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

/**
 * Viewer routes: the task attachment list plus a content endpoint that
 * answers per (format, page) from the supplied map; `contentError`
 * forces every content request to fail with the given envelope.
 */
function viewerHarness(
  attachments: unknown[],
  contentRespond: (info: { search: string }) => Response,
): { calls: Array<{ pathname: string; search: string }>; streams: SseConnection[] } {
  const streams: SseConnection[] = [];
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf(attachments)),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/attachments\/[^/]+\/content(\?|$)/,
      respond: contentRespond,
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
      respond: () => jsonResponse(pageOf([])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
      respond: () => jsonResponse(makeTask()),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => {
        const connection = sseConnection();
        streams.push(connection);
        return connection.response;
      },
    },
  ]);
  return { calls, streams };
}

const contentCalls = (calls: Array<{ pathname: string; search: string }>) =>
  calls.filter((call) => call.pathname.includes('/content'));

describe('AttachmentViewer (MT-4.6-04)', () => {
  it('renders every row with size and all four processing statuses, failure reason on failed', async () => {
    viewerHarness(
      [
        makeAttachment({ id: 'a-up', filename: 'up.png', processing_status: 'uploaded' }),
        makeAttachment({ id: 'a-proc', filename: 'proc.png', processing_status: 'processing' }),
        makeAttachment({ id: 'a-ok', filename: 'ok.png', processing_status: 'ready' }),
        makeAttachment({
          id: 'a-bad',
          filename: 'bad.png',
          processing_status: 'failed',
          failure_reason: 'OCR engine rejected the file',
        }),
      ],
      () => jsonResponse(makeAttachmentContent()),
    );
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getAllByTestId('attachment-row')).toHaveLength(4));

    const statuses = screen.getAllByTestId('attachment-status');
    expect(statuses.map((chip) => chip.getAttribute('data-status'))).toEqual([
      'uploaded',
      'processing',
      'ready',
      'failed',
    ]);
    expect(statuses[3].textContent).toBe('Failed');
    expect(screen.getByTestId('attachment-failure-reason').textContent).toBe(
      'OCR engine rejected the file',
    );
    // FR-ATT-03 size surfaced in KB.
    expect(screen.getAllByTestId('attachment-size')[0].textContent).toBe('2 KB');
    expect(screen.getByTestId('attachment-count').textContent).toContain('4');
  });

  it('renders the empty state when the task has no attachments', async () => {
    viewerHarness([], () => jsonResponse(makeAttachmentContent()));
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByText('No attachments')).toBeTruthy());
  });

  it('renders a distinct loading state while the list is pending', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
        respond: () => new Promise<Response>(() => {}),
      },
    ]);
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    expect(screen.getByText('Loading attachments…')).toBeTruthy();
  });

  it('shows an image preview fetched as a data URL with OCR and description tabs (P10 inert)', async () => {
    viewerHarness(
      [makeAttachment({ id: 'att-img', filename: 'diagram.png', is_image: true })],
      ({ search }) => {
        const params = new URLSearchParams(search);
        if (params.get('format') === 'image_base64') {
          return jsonResponse(
            makeAttachmentContent({
              attachment_id: 'att-img',
              format: 'image_base64',
              image_base64: 'aGVsbG8=',
              media_type: 'image/png',
            }),
          );
        }
        return jsonResponse(
          makeAttachmentContent({
            attachment_id: 'att-img',
            format: 'text_ocr',
            content: 'OCR transcript text',
            description: 'A flow chart of the login sequence',
          }),
        );
      },
    );
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-select')).toBeTruthy());
    fireEvent.click(screen.getByTestId('attachment-select'));

    // Auth-aware fetch → data: URL, never a second cookie-less request.
    await waitFor(() => expect(screen.getByTestId('attachment-image')).toBeTruthy());
    expect(screen.getByTestId('attachment-image').getAttribute('src')).toBe(
      'data:image/png;base64,aGVsbG8=',
    );
    // OCR tab is the default text view; the transcript renders inertly.
    expect(screen.getByTestId('attachment-ocr-text').textContent).toBe('OCR transcript text');
    expect(screen.getByTestId('untrusted-content-banner')).toBeTruthy();
    // Description tab appears when the pipeline produced one.
    const descriptionTab = screen.getByTestId('attachment-tab-description');
    fireEvent.click(descriptionTab);
    expect(screen.getByTestId('attachment-description-text').textContent).toBe(
      'A flow chart of the login sequence',
    );
    // Every text pane carries the untrusted treatment (Principle P10).
    const descriptionPane = screen.getByTestId('attachment-description-pane');
    expect(within(descriptionPane).getByTestId('untrusted-content-banner')).toBeTruthy();
  });

  it('hides the description tab when no description exists anywhere (MT risk note)', async () => {
    viewerHarness(
      [
        makeAttachment({
          id: 'att-img',
          filename: 'bare.png',
          is_image: true,
          short_description: null,
        }),
      ],
      ({ search }) => {
        const params = new URLSearchParams(search);
        if (params.get('format') === 'image_base64') {
          return jsonResponse(
            makeAttachmentContent({ image_base64: 'aGVsbG8=', media_type: 'image/png' }),
          );
        }
        return jsonResponse(makeAttachmentContent({ format: 'text_ocr', content: 'raw ocr' }));
      },
    );
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-select')).toBeTruthy());
    fireEvent.click(screen.getByTestId('attachment-select'));
    await waitFor(() => expect(screen.getByTestId('attachment-tab-ocr')).toBeTruthy());
    expect(screen.queryByTestId('attachment-tab-description')).toBeNull();
  });

  it('navigates document pages with page_number/total_pages honored (one page per request)', async () => {
    const { calls } = viewerHarness(
      [makeAttachment({ id: 'att-doc', filename: 'spec.md', is_image: false })],
      ({ search }) => {
        const page = Number(new URLSearchParams(search).get('page') ?? '1');
        return jsonResponse(
          makeAttachmentContent({
            attachment_id: 'att-doc',
            format: 'markdown',
            content: `Markdown page ${page}`,
            page_number: page,
            total_pages: 2,
          }),
        );
      },
    );
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-select')).toBeTruthy());
    fireEvent.click(screen.getByTestId('attachment-select'));

    await waitFor(() =>
      expect(screen.getByTestId('attachment-page-indicator').textContent).toBe('Page 1 of 2'),
    );
    expect(screen.getByTestId('attachment-page-prev').hasAttribute('disabled')).toBe(true);
    expect(screen.getByTestId('attachment-page-next').hasAttribute('disabled')).toBe(false);
    expect(screen.getByTestId('untrusted-content-banner')).toBeTruthy();

    fireEvent.click(screen.getByTestId('attachment-page-next'));
    await waitFor(() =>
      expect(screen.getByTestId('attachment-page-indicator').textContent).toBe('Page 2 of 2'),
    );
    // RISK-13: page 2 was its own request, never a whole-document preload.
    const pages = contentCalls(calls).map((call) => new URLSearchParams(call.search).get('page'));
    expect(pages).toEqual(['1', '2']);
    expect(screen.getByTestId('attachment-page-next').hasAttribute('disabled')).toBe(true);
    expect(screen.getByTestId('attachment-page-prev').hasAttribute('disabled')).toBe(false);

    fireEvent.click(screen.getByTestId('attachment-page-prev'));
    await waitFor(() =>
      expect(screen.getByTestId('attachment-page-indicator').textContent).toBe('Page 1 of 2'),
    );
  });

  it('maps ATTACHMENT_NOT_READY to the catalog state with a working retry (MT risk note)', async () => {
    let attempts = 0;
    const { calls } = viewerHarness(
      [makeAttachment({ id: 'att-doc', filename: 'spec.md', is_image: false })],
      () => {
        attempts += 1;
        if (attempts === 1) {
          return errorResponse('ATTACHMENT_NOT_READY', 409);
        }
        return jsonResponse(
          makeAttachmentContent({
            content: 'Ready now',
            page_number: 1,
            total_pages: 1,
          }),
        );
      },
    );
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-select')).toBeTruthy());
    fireEvent.click(screen.getByTestId('attachment-select'));

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Attachment not ready');
    expect(alert.textContent).toContain(
      'This attachment is still being processed. Wait for it to finish, then try again.',
    );

    // Retry = content refetch (Section 9.2 exposes no reprocess endpoint).
    fireEvent.click(screen.getByText('Try again'));
    await waitFor(() => expect(screen.getByTestId('markdown-preview')).toBeTruthy());
    expect(contentCalls(calls)).toHaveLength(2);
  });

  it('maps ATTACHMENT_UNSUPPORTED_FORMAT to the catalog state', async () => {
    viewerHarness([makeAttachment({ id: 'att-doc', filename: 'weird.bin', is_image: false })], () =>
      errorResponse('ATTACHMENT_UNSUPPORTED_FORMAT', 415),
    );
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-select')).toBeTruthy());
    fireEvent.click(screen.getByTestId('attachment-select'));
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByRole('alert').textContent).toContain('Unsupported file');
  });

  it('updates a row live on attachment.ready with zero list refetches (Section 9.6)', async () => {
    const attachment = makeAttachment({ id: 'att-1', processing_status: 'processing' });
    const { calls, streams } = viewerHarness([attachment], () =>
      jsonResponse(makeAttachmentContent()),
    );
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-status')).toBeTruthy());
    expect(screen.getByTestId('attachment-status').getAttribute('data-status')).toBe('processing');
    const listCalls = () =>
      calls.filter((call) => /\/attachments(\?|$)/.test(call.pathname + call.search));

    streams[0].frame(
      4,
      makeEventEnvelope({
        id: 4,
        type: 'attachment.ready',
        task_id: TASK_ID,
        data: { attachment_id: 'att-1' },
      }),
    );

    await waitFor(() =>
      expect(screen.getByTestId('attachment-status').getAttribute('data-status')).toBe('ready'),
    );
    // Acceptance: status moved through the cache patch, not a refetch.
    expect(listCalls()).toHaveLength(1);
  });

  it('shows the pipeline failure_reason on a live attachment.failed event', async () => {
    const attachment = makeAttachment({ id: 'att-1', processing_status: 'processing' });
    const { streams } = viewerHarness([attachment], () => jsonResponse(makeAttachmentContent()));
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByTestId('attachment-status')).toBeTruthy());

    streams[0].frame(
      5,
      makeEventEnvelope({
        id: 5,
        type: 'attachment.failed',
        task_id: TASK_ID,
        data: { attachment_id: 'att-1', reason: 'Unsupported encoding' },
      }),
    );

    await waitFor(() =>
      expect(screen.getByTestId('attachment-failure-reason').textContent).toBe(
        'Unsupported encoding',
      ),
    );
  });

  it('maps list errors to catalog copy only', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
        respond: () => errorResponse('SERVER_ERROR', 500, 'raw traceback'),
      },
    ]);
    renderWithQueryClient(<AttachmentViewer pid={PID} taskId={TASK_ID} />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(alert.textContent).not.toContain('raw traceback');
  });
});
