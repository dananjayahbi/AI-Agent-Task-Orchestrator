'use client';

/**
 * Attachment viewer (MT-4.6-04; Section 13.2 "Attachment viewer: image
 * preview with OCR and description tabs; document pages; processing
 * status and retry"; Section 9.5 retrieval table; Principle P10).
 *
 * Structure:
 *  - the list shows every attachment row with its `processing_status`
 *    (`uploaded` / `processing` / `ready` / `failed`) and the pipeline's
 *    human-readable `failure_reason` on failures (Section 7.2 /
 *    FR-ATT-07). Status moves live through `attachment.ready|failed`
 *    events patched into the same cache entry by the detail view's
 *    single SSE sink — there is deliberately no poll (WP-4.5
 *    discipline, reused here);
 *  - images render the normalized bytes (`format=image_base64`) as a
 *    `data:` URL — fetched through the generated client's credentialed
 *    transport, so the browser never issues a cookie-less image
 *    request (MT risk note; §9.5/13.2) — with two tabs: **OCR**
 *    (`text_ocr` transcript) and **description** (`description` /
 *    `layout_caption` content; the tab hides entirely when the
 *    provider produced none — MT risk note);
 *  - documents page through `markdown` with `page_number` /
 *    `total_pages` honored (WP-4.6 acceptance "attachment pages
 *    navigable"), one page per request (RISK-13);
 *  - all text-derived panes carry the untrusted-content banner and
 *    render inertly (markdown through the inert `MarkdownPreview`,
 *    never executed; P10);
 *  - "Retry" per the MT risk note is a status/content refresh — Section
 *    9.2 exposes no manual reprocess endpoint, so none is invented;
 *  - `ATTACHMENT_NOT_READY` / `ATTACHMENT_UNSUPPORTED_FORMAT` map to
 *    catalog copy only (Section 20.4 item 5).
 */
import { useState } from 'react';

import { MarkdownPreview } from '@/components/task/markdown-preview';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/errors/error-state';
import { EmptyState } from '@/components/states/empty-state';
import { LoadingState } from '@/components/states/loading-state';
import { UntrustedContentBanner } from '@/components/task/detail/untrusted-content-banner';
import type { Attachment } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { useAttachmentContentQuery } from '@/lib/queries/attachment-content';
import { useTaskAttachmentsQuery } from '@/lib/queries/attachments';
import { cn } from 'cn';

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Uploaded',
  processing: 'Processing…',
  ready: 'Ready',
  failed: 'Failed',
};

const STATUS_CLASSES: Record<string, string> = {
  uploaded: 'bg-muted text-muted-foreground',
  processing: 'animate-pulse bg-secondary text-secondary-foreground',
  ready: 'bg-primary text-primary-foreground',
  failed: 'bg-destructive text-destructive-foreground',
};

export function AttachmentStatusChip({ status }: { status: string }) {
  return (
    <span
      data-testid="attachment-status"
      data-status={status}
      aria-label={`Processing status: ${STATUS_LABELS[status] ?? status}`}
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold',
        STATUS_CLASSES[status] ?? 'bg-muted text-muted-foreground',
      )}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

/** Friendly per-code copy for the content endpoint's two catalog errors. */
function ContentError({ error, onRetry }: { error: unknown; onRetry?: (() => void) | undefined }) {
  const friendly = resolveError(error);
  return (
    <ErrorState
      title={friendly.title}
      message={friendly.message}
      requestId={friendly.requestId}
      onRetry={onRetry}
    />
  );
}

/** Image pane: normalized preview plus OCR / description tabs (Section 13.2). */
function ImagePane({ attachment }: { attachment: Attachment }) {
  const [tab, setTab] = useState<'ocr' | 'description'>('ocr');
  const imageQuery = useAttachmentContentQuery(attachment.id, 'image_base64', null);
  const textQuery = useAttachmentContentQuery(attachment.id, 'text_ocr', null);

  const description =
    (typeof textQuery.data?.description === 'string' && textQuery.data.description !== ''
      ? textQuery.data.description
      : null) ??
    (attachment.short_description !== null && attachment.short_description !== ''
      ? attachment.short_description
      : null);

  return (
    <div className="grid gap-3" data-testid="attachment-image-pane">
      {imageQuery.isPending ? (
        <LoadingState label="Loading image…" />
      ) : imageQuery.isError ? (
        <ContentError error={imageQuery.error} onRetry={() => void imageQuery.refetch()} />
      ) : (
        // data: URL from the fetched base64 — no second, uncredentialed request.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          data-testid="attachment-image"
          src={`data:${imageQuery.data.media_type ?? 'image/png'};base64,${imageQuery.data.image_base64 ?? ''}`}
          alt={attachment.filename}
          className="max-h-96 self-start rounded-md border border-border"
        />
      )}

      <div role="tablist" aria-label="Attachment text views" className="flex gap-1">
        <Button
          role="tab"
          size="sm"
          variant={tab === 'ocr' ? 'default' : 'outline'}
          aria-selected={tab === 'ocr'}
          data-testid="attachment-tab-ocr"
          onClick={() => setTab('ocr')}
        >
          OCR
        </Button>
        {description !== null && (
          <Button
            role="tab"
            size="sm"
            variant={tab === 'description' ? 'default' : 'outline'}
            aria-selected={tab === 'description'}
            data-testid="attachment-tab-description"
            onClick={() => setTab('description')}
          >
            Description
          </Button>
        )}
      </div>

      {tab === 'ocr' ? (
        <div className="grid gap-2" data-testid="attachment-ocr-pane">
          <UntrustedContentBanner />
          {textQuery.isPending ? (
            <LoadingState label="Running OCR view…" />
          ) : textQuery.isError ? (
            <ContentError error={textQuery.error} onRetry={() => void textQuery.refetch()} />
          ) : (
            <pre
              data-testid="attachment-ocr-text"
              className="overflow-x-auto rounded-md border border-border bg-background/40 p-3 text-xs whitespace-pre-wrap"
            >
              {textQuery.data.content ?? ''}
            </pre>
          )}
        </div>
      ) : (
        description !== null && (
          <div className="grid gap-2" data-testid="attachment-description-pane">
            <UntrustedContentBanner />
            <p data-testid="attachment-description-text" className="text-sm break-words">
              {description}
            </p>
          </div>
        )
      )}
    </div>
  );
}

/** Document pane: one markdown page per request, pages navigable (Section 9.5). */
function DocumentPane({ attachment }: { attachment: Attachment }) {
  const [page, setPage] = useState(1);
  const pageQuery = useAttachmentContentQuery(attachment.id, 'markdown', page);

  const shown = pageQuery.data?.page_number ?? page;
  const total = pageQuery.data?.total_pages ?? null;

  return (
    <div className="grid gap-3" data-testid="attachment-document-pane">
      <UntrustedContentBanner />
      {pageQuery.isPending ? (
        <LoadingState label="Loading page…" />
      ) : pageQuery.isError ? (
        <ContentError error={pageQuery.error} onRetry={() => void pageQuery.refetch()} />
      ) : (
        <MarkdownPreview source={pageQuery.data.content ?? ''} />
      )}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          data-testid="attachment-page-prev"
          disabled={shown <= 1}
          onClick={() => setPage(shown - 1)}
        >
          Previous
        </Button>
        <span data-testid="attachment-page-indicator" className="text-xs text-muted-foreground">
          {total === null ? `Page ${shown}` : `Page ${shown} of ${total}`}
        </span>
        <Button
          size="sm"
          variant="outline"
          data-testid="attachment-page-next"
          disabled={total !== null && shown >= total}
          onClick={() => setPage(shown + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}

type AttachmentViewerProps = {
  pid: string;
  taskId: string;
};

export function AttachmentViewer({ pid, taskId }: AttachmentViewerProps) {
  const listQuery = useTaskAttachmentsQuery(pid, taskId);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (listQuery.isPending) {
    return <LoadingState label="Loading attachments…" />;
  }
  if (listQuery.isError) {
    const friendly = resolveError(listQuery.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void listQuery.refetch()}
      />
    );
  }

  const rows = listQuery.data ?? [];
  if (rows.length === 0) {
    return (
      <EmptyState
        title="No attachments"
        description="Files attached to this task will appear here."
      />
    );
  }

  return (
    <div className="grid gap-3" data-testid="attachment-viewer">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">
          Attachments{' '}
          <span data-testid="attachment-count" className="font-normal text-muted-foreground">
            ({rows.length})
          </span>
        </h3>
        <Button
          size="sm"
          variant="outline"
          data-testid="attachment-refresh"
          onClick={() => void listQuery.refetch()}
        >
          Refresh status
        </Button>
      </div>

      <ul data-testid="attachment-list" className="grid gap-2">
        {rows.map((row) => (
          <li
            key={row.id}
            data-testid="attachment-row"
            data-attachment-id={row.id}
            className={cn(
              'rounded-md border bg-card p-2.5 text-card-foreground',
              row.id === selectedId ? 'border-ring ring-2 ring-ring/40' : 'border-border',
            )}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <button
                type="button"
                data-testid="attachment-select"
                aria-label={`View ${row.filename}`}
                aria-pressed={row.id === selectedId}
                onClick={() => setSelectedId(row.id === selectedId ? null : row.id)}
                className="truncate text-left text-sm font-medium text-foreground underline-offset-2 hover:underline focus-visible:outline-2 focus-visible:outline-ring"
              >
                {row.filename}
              </button>
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                <span data-testid="attachment-size">
                  {Math.max(1, Math.round(row.size / 1024))} KB
                </span>
                <AttachmentStatusChip status={row.processing_status} />
              </div>
            </div>
            {row.processing_status === 'failed' && row.failure_reason !== null && (
              <p data-testid="attachment-failure-reason" className="mt-1 text-xs text-destructive">
                {row.failure_reason}
              </p>
            )}
            {row.id === selectedId &&
              (row.is_image ? (
                <div className="mt-3 border-t border-border pt-3">
                  <ImagePane attachment={row} />
                </div>
              ) : (
                <div className="mt-3 border-t border-border pt-3">
                  <DocumentPane attachment={row} />
                </div>
              ))}
          </li>
        ))}
      </ul>
    </div>
  );
}
