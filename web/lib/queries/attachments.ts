/**
 * Attachment rows for the task modal (MT-4.5-05; Section 9.2 `GET
 * /tasks/{id}/attachments`, `DELETE /attachments/{id}`; Section 13.3
 * cache discipline).
 *
 * Status discipline (FR-ATT-07; WP-4.5 deliverable "status via stream
 * events"): the initial list load is the only fetch — every subsequent
 * `processing_status` change arrives as an `attachment.*` Section 9.6
 * event through `useBoardLiveUpdates` (WP-4.3) and is applied here via
 * `applyAttachmentEvent`. There is deliberately no refetch/polling path
 * for status; if the stream drops, the rows simply hold their last known
 * status and the stream indicator tells the operator why.
 */
import { keepPreviousData, useQuery, type QueryClient } from '@tanstack/react-query';

import { callApi, deleteAttachment, listTaskAttachments, uploadAttachment } from '@/lib/api';
import { fetchAllPages } from '@/lib/api/pagination';
import type { Attachment, EventEnvelope } from '@/lib/api/generated/types.gen';
import { queryKeys } from '@/lib/queries/keys';

/** Every non-deleted row for the task (cursor to the end — max 10, Section 9.5). */
export async function fetchTaskAttachments(pid: string, taskId: string): Promise<Attachment[]> {
  return fetchAllPages((cursor) =>
    callApi(
      listTaskAttachments({
        path: { id: taskId },
        query: { page_size: 100, ...(cursor === undefined ? {} : { cursor }) },
      }),
    ).then((page) => ({ results: page.results, next_cursor: page.next_cursor })),
  );
}

/**
 * `taskId === null` (create mode) yields a disabled placeholder — the
 * upload endpoint requires a task id, so nothing loads until the draft
 * exists (MT risk note: no phantom uploads).
 */
export function useTaskAttachmentsQuery(pid: string, taskId: string | null) {
  return useQuery({
    queryKey: queryKeys.taskAttachments(pid, taskId ?? 'pending'),
    queryFn: () => fetchTaskAttachments(pid, taskId ?? ''),
    enabled: taskId !== null,
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });
}

/** One multipart upload through the generated client (FormData `{file}`). */
export function uploadTaskAttachment(taskId: string, file: File): Promise<Attachment> {
  const form = { file };
  return callApi(uploadAttachment({ path: { id: taskId }, body: form as never }));
}

export function deleteTaskAttachment(attachmentId: string): Promise<void> {
  return callApi(deleteAttachment({ path: { id: attachmentId } })).then(() => undefined);
}

type AttachmentEventData = {
  attachment_id?: unknown;
  reason?: unknown;
};

function readEventTarget(event: EventEnvelope): { id: string; reason: string | null } | null {
  const data = event.data as AttachmentEventData | null | undefined;
  if (typeof data?.attachment_id !== 'string' || data.attachment_id === '') {
    return null;
  }
  return {
    id: data.attachment_id,
    reason: typeof data.reason === 'string' ? data.reason : null,
  };
}

/**
 * Pure reducer: one Section 9.6 `attachment.*` envelope applied to the
 * cached rows. Unknown ids and unrelated events return the input
 * untouched — the next list load reconciles anything this missed.
 */
export function applyAttachmentEvent(
  rows: readonly Attachment[],
  event: EventEnvelope,
): Attachment[] {
  const target = readEventTarget(event);
  if (target === null) return rows as Attachment[];

  let changed = false;
  const next = rows.map((row) => {
    if (row.id !== target.id) return row;
    changed = true;
    if (event.type === 'attachment.processing') {
      return { ...row, processing_status: 'processing' };
    }
    if (event.type === 'attachment.ready') {
      return { ...row, processing_status: 'ready', failure_reason: null };
    }
    // attachment.failed — FR-ATT-07: the pipeline reason stays visible.
    return { ...row, processing_status: 'failed', failure_reason: target.reason };
  });
  return changed ? next : (rows as Attachment[]);
}

/**
 * Patch every cached attachment list this event belongs to (WP-4.3's
 * `useBoardLiveUpdates` calls this from the page's single SSE sink —
 * one connection, never a second one from the modal). Key shape:
 * `['projects', pid, 'tasks', taskId, 'attachments']`.
 */
export function patchAttachmentCaches(client: QueryClient, event: EventEnvelope): void {
  if (
    event.type !== 'attachment.processing' &&
    event.type !== 'attachment.ready' &&
    event.type !== 'attachment.failed'
  ) {
    return;
  }
  client.setQueriesData<Attachment[]>(
    {
      predicate: (query) => {
        const key = query.queryKey;
        return (
          key.length === 5 &&
          key[0] === 'projects' &&
          key[1] === event.project_id &&
          key[2] === 'tasks' &&
          key[3] === event.task_id &&
          key[4] === 'attachments'
        );
      },
    },
    (rows) => (rows === undefined ? rows : applyAttachmentEvent(rows, event)),
  );
}
