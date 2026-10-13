'use client';

/**
 * Publish action with the T2 readiness gate (MT-4.5-06; Section 8.2 T2;
 * FR-ATT-07).
 *
 * The moment modal, uploader and state machine meet:
 *  - the gate (`lib/task/publish-gate.ts`) mirrors the server's T2
 *    guards — required fields, attachments `ready` (or explicit
 *    override), completed dependencies — the server stays the authority;
 *  - per-file statuses come from the same stream-patched cache the
 *    dropzone renders, so `attachment.ready|failed` events update the
 *    gate live (Section 9.6; no polling);
 *  - the override is never the default: the "publish anyway" checkbox
 *    appears only when every blocker is attachment-readiness, must be
 *    consciously ticked, and carries `override: true` through the
 *    transport seam (FR-ATT-07 "explicitly overridden");
 *  - the actual send goes through the MT-4.5-06 seam
 *    (`publish-seam.ts`) — `POST /tasks/{id}/transition` is not in the
 *    published schema yet (OQ), so an unwired seam shows an explicit
 *    notice instead of a silent no-op (WP-4.4 precedent).
 */
import { useState } from 'react';
import { useQueries, useQueryClient } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import type { Task } from '@/lib/api/generated/types.gen';
import { STATE_LABELS } from '@/lib/board/states';
import { resolveError } from '@/lib/errors';
import { evaluatePublishGate, publishBlockerMessage } from '@/lib/task/publish-gate';
import { publishUnavailableNotice, type PublishTransport } from '@/lib/task/publish-seam';
import type { TaskFormValues } from '@/lib/forms/task-schemas';
import { useTaskAttachmentsQuery } from '@/lib/queries/attachments';
import { fetchTaskRow } from '@/lib/queries/tasks';
import { queryKeys } from '@/lib/queries/keys';

type PublishActionProps = {
  pid: string;
  task: Task;
  /** Current form values (dependency guard + title validity). */
  values: TaskFormValues;
  dirty: boolean;
  /**
   * MT-4.5-06 seam: the eventual consumer sends
   * `POST /tasks/{id}/transition` (T2 publish). Absent → explicit
   * unavailable notice (never a silent no-op).
   */
  transport?: PublishTransport | undefined;
  /** Called after a successful publish (cache refresh hook). */
  onPublished?: () => void;
};

export function PublishAction({
  pid,
  task,
  values,
  dirty,
  transport,
  onPublished,
}: PublishActionProps) {
  const queryClient = useQueryClient();
  const [override, setOverride] = useState(false);
  const [notice, setNotice] = useState<{ kind: 'info' | 'error' | 'success'; text: string } | null>(
    null,
  );
  const [sending, setSending] = useState(false);

  const attachmentsQuery = useTaskAttachmentsQuery(pid, task.id);

  // Dependency rows share the picker's cache keys (MT-4.5-04) — one
  // fetch per dependency, refreshed by the same invalidations.
  const depRows = useQueries({
    queries: values.depends_on.map((depId) => ({
      queryKey: ['projects', pid, 'tasks', depId, 'row'] as const,
      queryFn: () => fetchTaskRow(depId),
      staleTime: 30_000,
    })),
  });

  const gate = evaluatePublishGate({
    state: task.state,
    dirty,
    titleValid: values.title.trim() !== '',
    attachments: attachmentsQuery.data,
    dependencies: values.depends_on.map((depId, index) => {
      const row = depRows[index];
      return {
        id: depId,
        status:
          row === undefined || row.isPending
            ? ('unknown' as const)
            : row.isError
              ? ('incomplete' as const) // a row we cannot load is not verified complete
              : row.data.state === 'completed'
                ? ('completed' as const)
                : ('incomplete' as const),
      };
    }),
  });

  const blocked = !gate.canPublish && !(override && gate.overrideCovers);

  async function publish() {
    setSending(true);
    try {
      if (transport === undefined) {
        setNotice({ kind: 'info', text: publishUnavailableNotice(task.id) });
        return;
      }
      await transport({ taskId: task.id, version: task.version, override });
      setNotice({
        kind: 'success',
        text: `Published — ${task.id} is now ${STATE_LABELS.pending} and visible to agents.`,
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.boardTasksRoot(pid) });
      onPublished?.();
    } catch (error) {
      // Section 13.3: catalog copy only — VERSION_CONFLICT and
      // TASK_STATE_CONFLICT carry refresh guidance.
      setNotice({ kind: 'error', text: resolveError(error).message });
    } finally {
      setSending(false);
    }
  }

  return (
    <section
      data-testid="publish-action"
      aria-label="Publish"
      className="grid gap-2 rounded-md border border-border p-3"
    >
      <p className="text-sm font-medium text-foreground">Publish (T2)</p>

      {gate.blockers.length > 0 && (
        <ul aria-label="Publish blockers" className="grid gap-1">
          {gate.blockers.map((blocker) => (
            <li
              key={blocker.kind}
              data-testid={`publish-blocker-${blocker.kind}`}
              className="text-xs text-muted-foreground"
            >
              {publishBlockerMessage(blocker)}
            </li>
          ))}
        </ul>
      )}

      {gate.overrideCovers && (
        <label className="flex items-start gap-2 text-xs text-foreground">
          <input
            type="checkbox"
            data-testid="publish-override"
            checked={override}
            onChange={(event) => setOverride(event.target.checked)}
            className="mt-0.5"
          />
          <span>
            Publish anyway — I understand some attachments are not ready (explicit override,
            FR-ATT-07).
          </span>
        </label>
      )}

      <div className="flex items-center gap-2">
        <Button
          type="button"
          data-testid="publish-button"
          disabled={blocked || sending}
          onClick={() => void publish()}
        >
          {sending ? 'Publishing…' : 'Publish'}
        </Button>
        {override && gate.overrideCovers && (
          <span data-testid="publish-override-badge" className="text-xs text-muted-foreground">
            override will be recorded
          </span>
        )}
      </div>

      {notice !== null && (
        <p
          role={notice.kind === 'error' ? 'alert' : 'status'}
          data-testid="publish-notice"
          data-kind={notice.kind}
          className={
            notice.kind === 'error' ? 'text-xs text-destructive' : 'text-xs text-muted-foreground'
          }
        >
          {notice.text}
        </p>
      )}
    </section>
  );
}
