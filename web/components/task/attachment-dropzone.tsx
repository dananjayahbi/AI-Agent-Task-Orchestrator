'use client';

/**
 * Attachment dropzone with per-file progress and processing status
 * (MT-4.5-05; Section 13.2 "attachment dropzone with per-file processing
 * status"; FR-ATT-07).
 *
 * Behaviour:
 *  - drag-and-drop and file-picker upload to `POST /tasks/{id}/attachments`
 *    through the generated client (FormData `file` part — NFR-11);
 *  - Section 9.5 pre-checks mirror the server limits for instant
 *    feedback (25 MB / 10 per task / 100 MB total / type allowlist) —
 *    the server stays the authority (content sniffing, WP-1.11);
 *  - per-file *upload* progress is phase-based: the fetch layer offers
 *    no byte-level upload hook (documented in the WP changelog), so a
 *    file shows "Uploading…" while its request is in flight and switches
 *    to the server's `uploaded` row on the 201 response;
 *  - *processing* status (`uploaded → processing → ready|failed`) comes
 *    exclusively from the `attachment.*` stream events patched into the
 *    query cache (MT-4.5-05 "no polling" rule) — `failed` keeps the
 *    pipeline's human-readable reason visible (FR-ATT-07) with a
 *    remove affordance (`DELETE /attachments/{id}`);
 *  - create-mode sequencing: with no task id yet the dropzone queues
 *    files locally; uploads start only after the draft exists (the
 *    endpoint requires the id), and a cancelled create uploads nothing.
 */
import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import {
  ALLOWED_ATTACHMENT_LABELS,
  MAX_ATTACHMENT_BYTES,
  MAX_ATTACHMENTS_PER_TASK,
  MAX_TOTAL_BYTES,
  precheckAttachment,
} from '@/lib/attachments/limits';
import type { Attachment } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import {
  deleteTaskAttachment,
  uploadTaskAttachment,
  useTaskAttachmentsQuery,
} from '@/lib/queries/attachments';
import { queryKeys } from '@/lib/queries/keys';
import { cn } from 'cn';

type AttachmentDropzoneProps = {
  pid: string;
  /** `null` while creating (T1) — files queue until the draft exists. */
  taskId: string | null;
};

type QueuedFile = {
  localId: string;
  file: File;
  /** The task this file was queued against; null = waiting for a draft. */
  taskId: string | null;
};

type RejectedFile = {
  localId: string;
  name: string;
  message: string;
};

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Uploaded',
  processing: 'Processing…',
  ready: 'Ready',
  failed: 'Failed',
};

let localCounter = 0;
function nextLocalId(): string {
  localCounter += 1;
  return `local-${localCounter}`;
}

export function AttachmentDropzone({ pid, taskId }: AttachmentDropzoneProps) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const attachmentsQuery = useTaskAttachmentsQuery(pid, taskId);
  const rows = attachmentsQuery.data ?? [];

  const [queued, setQueued] = useState<QueuedFile[]>([]);
  const [rejected, setRejected] = useState<RejectedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  // Local ids already handed to the mutation — the effect uses this to
  // dispatch create-mode files exactly once without a nested setState.
  const dispatchedRef = useRef<Set<string>>(new Set());

  // One mutation per queued file; each row is removed from the local
  // queue when its request settles, and a server rejection records the
  // canonical (catalog-mapped) message per file.
  const upload = useMutation({
    mutationFn: ({ taskId: id, file }: { taskId: string; file: File }) =>
      uploadTaskAttachment(id, file),
    onSuccess: (attachment) => {
      queryClient.setQueryData<Attachment[]>(
        queryKeys.taskAttachments(pid, attachment.task_id),
        (current) => {
          const list = current ?? [];
          return list.some((row) => row.id === attachment.id) ? list : [...list, attachment];
        },
      );
    },
    onError: (error, variables) => {
      setRejected((current) => [
        ...current,
        {
          localId: nextLocalId(),
          name: variables.file.name,
          message: resolveError(error).message,
        },
      ]);
    },
  });

  const remove = useMutation({
    mutationFn: (attachmentId: string) => deleteTaskAttachment(attachmentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.taskAttachments(pid, taskId ?? 'pending'),
      });
    },
  });

  function acceptFiles(files: FileList | null) {
    if (files === null) return;
    const existingBytes = rows.reduce((sum, row) => sum + row.size, 0);
    const nextQueued: { localId: string; file: File }[] = [];
    const nextRejected: RejectedFile[] = [];
    let queuedBytes = 0;

    for (const file of Array.from(files)) {
      const verdict = precheckAttachment(file, {
        existingCount: rows.length + nextQueued.length,
        existingTotalBytes: existingBytes,
        queuedTotalBytes: queuedBytes,
      });
      if (!verdict.ok) {
        nextRejected.push({ localId: nextLocalId(), name: file.name, message: verdict.message });
        continue;
      }
      queuedBytes += file.size;
      nextQueued.push({ localId: nextLocalId(), file });
    }

    setRejected((current) => [...current, ...nextRejected]);

    // Queued rows double as the per-file "Uploading…" progress rows; each
    // is removed when its request settles. Create mode records a null
    // task id and waits for the draft (no phantom uploads).
    const stamped = nextQueued.map((entry) => ({ ...entry, taskId }));
    setQueued((current) => [...current, ...stamped]);
    if (taskId !== null) {
      startUploads(taskId, stamped);
    }
  }

  function startUploads(id: string, files: QueuedFile[]) {
    for (const entry of files) {
      upload.mutate(
        { taskId: id, file: entry.file },
        {
          onSettled: () =>
            setQueued((current) => current.filter((q) => q.localId !== entry.localId)),
        },
      );
    }
  }

  // Create→edit hand-off: the board swaps the saved task in; files
  // queued against no task now have an id to upload against (MT risk
  // note: explicit sequence, no orphans). Dispatch is idempotent via the
  // ref — no nested setState in the effect body.
  useEffect(() => {
    if (taskId === null) return;
    const pending = queued.filter(
      (entry) => entry.taskId === null && !dispatchedRef.current.has(entry.localId),
    );
    if (pending.length === 0) return;
    for (const entry of pending) dispatchedRef.current.add(entry.localId);
    startUploads(taskId, pending);
    // `startUploads` only reads the stable mutation's `mutate`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, queued]);

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragOver(false);
    acceptFiles(event.dataTransfer.files);
  }

  return (
    <div data-testid="attachment-dropzone" className="grid gap-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Add attachments: drop files here or press Enter to pick files"
        data-testid="dropzone-surface"
        data-dragover={dragOver}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          'cursor-pointer rounded-md border-2 border-dashed p-4 text-center',
          'text-sm text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring',
          dragOver ? 'border-foreground bg-muted/40' : 'border-border',
        )}
      >
        {taskId === null
          ? 'Queue attachments — they upload after the draft task is created.'
          : 'Drop files here or click to pick.'}
        <span className="mt-1 block text-xs">
          Up to {MAX_ATTACHMENTS_PER_TASK} files, {MAX_ATTACHMENT_BYTES / (1024 * 1024)} MB each,{' '}
          {MAX_TOTAL_BYTES / (1024 * 1024)} MB total — {ALLOWED_ATTACHMENT_LABELS}.
        </span>
        <input
          ref={inputRef}
          type="file"
          multiple
          data-testid="dropzone-input"
          className="hidden"
          aria-label="Pick attachment files"
          onChange={(event) => {
            acceptFiles(event.target.files);
            event.target.value = '';
          }}
        />
      </div>

      {rejected.length > 0 && (
        <ul aria-label="Rejected files" className="grid gap-1">
          {rejected.map((entry) => (
            <li key={entry.localId} className="text-xs text-destructive">
              {entry.name !== '' && <span className="font-medium">{entry.name}: </span>}
              {entry.message}
            </li>
          ))}
        </ul>
      )}

      {queued.length > 0 && (
        <ul aria-label="Uploading files" className="grid gap-1">
          {queued.map((entry) => (
            <li key={entry.localId} className="flex items-center gap-2 text-sm">
              <span className="truncate text-foreground">{entry.file.name}</span>
              <span
                role="progressbar"
                aria-label={
                  taskId === null ? `Queued ${entry.file.name}` : `Uploading ${entry.file.name}`
                }
                data-testid={`upload-progress-${entry.localId}`}
                className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted"
              >
                <span className="h-full w-1/3 animate-pulse rounded-full bg-primary" />
              </span>
              <span className="text-xs text-muted-foreground">
                {taskId === null ? 'Waiting for draft…' : 'Uploading…'}
              </span>
            </li>
          ))}
        </ul>
      )}

      <ul aria-label="Task attachments" className="grid gap-1.5">
        {rows.map((row) => (
          <li
            key={row.id}
            data-testid={`attachment-row-${row.id}`}
            data-status={row.processing_status}
            className="rounded-md border border-border p-2"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm text-foreground">{row.filename}</span>
              <span className="flex items-center gap-2">
                <span
                  data-testid={`attachment-status-${row.id}`}
                  className={cn(
                    'rounded-full px-2 py-0.5 text-[11px] font-medium',
                    row.processing_status === 'ready' && 'bg-muted text-foreground',
                    row.processing_status === 'failed' &&
                      'bg-destructive/15 text-destructive font-semibold',
                    (row.processing_status === 'uploaded' ||
                      row.processing_status === 'processing') &&
                      'bg-muted text-muted-foreground',
                  )}
                >
                  {STATUS_LABELS[row.processing_status] ?? row.processing_status}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  data-testid={`attachment-remove-${row.id}`}
                  aria-label={`Remove attachment ${row.filename}`}
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(row.id)}
                >
                  Remove
                </Button>
              </span>
            </div>
            {row.processing_status === 'failed' && row.failure_reason !== null && (
              <p
                data-testid={`attachment-failure-${row.id}`}
                className="mt-1 text-xs text-destructive"
              >
                {row.failure_reason}
              </p>
            )}
          </li>
        ))}
      </ul>

      {attachmentsQuery.isError && (
        <p role="alert" className="text-xs text-destructive">
          {resolveError(attachmentsQuery.error).message}
        </p>
      )}
    </div>
  );
}
