'use client';

/**
 * Request-changes / reassign dialog (MT-4.4-03; Section 13.2 — the
 * `in_human_review` → `pending` drop "opens the request-changes/reassign
 * dialog"; Section 8.2 T16; Section 11.5).
 *
 * Two actions, exactly as the plan defines them:
 *  - `request_changes` — the note is **mandatory**, validated here before
 *    any request is sent (T16's guard also exists server-side; client
 *    validation is courtesy, never the gate) and becomes the task's
 *    `latest_feedback` for the next coder (Section 11.5);
 *  - `reassign` — returns the task to `pending` and clears the worker;
 *    the note is optional (it then becomes `latest_feedback`).
 *
 * Both send the `version` the dialog saw (Section 8.2 rule 3). Endpoint
 * failures keep the dialog open with catalog-mapped copy
 * (Section 13.3); Radix supplies focus trap, Escape and focus return
 * (Section 13.4).
 */
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { Task } from '@/lib/api/generated/types.gen';
import { resolveError } from '@/lib/errors';
import { noteValidationError } from '@/lib/review/review-decision';
import type { ReviewDecisionMutation } from '@/lib/queries/review-decision';

type RequestChangesDialogProps = {
  task: Task;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mutation: ReviewDecisionMutation;
};

export function RequestChangesDialog({
  task,
  open,
  onOpenChange,
  mutation,
}: RequestChangesDialogProps) {
  const [note, setNote] = useState('');
  const [noteError, setNoteError] = useState<string | null>(null);
  const pending = mutation.isPending;

  const showNoteError = (next: string): boolean => {
    const error = noteValidationError(next);
    setNoteError(error);
    return error === null;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="request-changes-dialog">
        <DialogHeader>
          <DialogTitle>Send {task.id} back for changes</DialogTitle>
          <DialogDescription>
            Request changes with a required note, or reassign the task — both return it to Pending
            and clear the current worker.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-foreground">{task.title}</span>
            <span className="font-mono text-[11px] text-muted-foreground">{task.id}</span>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="request-changes-note" className="text-xs text-muted-foreground">
              Note (required for request changes — shown to the next coder)
            </Label>
            <Textarea
              id="request-changes-note"
              data-testid="request-changes-note"
              value={note}
              rows={4}
              aria-invalid={noteError !== null}
              aria-describedby={noteError !== null ? 'request-changes-note-error' : undefined}
              onChange={(event) => {
                setNote(event.target.value);
                if (noteError !== null) {
                  setNoteError(null); // re-validate on the next action
                }
              }}
            />
            {noteError !== null && (
              <p
                id="request-changes-note-error"
                data-testid="request-changes-note-error"
                className="text-xs text-destructive"
              >
                {noteError}
              </p>
            )}
          </div>
        </div>

        {mutation.isError && (
          <div
            role="alert"
            data-testid="request-changes-error"
            className="rounded-md border border-destructive/40 bg-destructive/10 p-2.5 text-sm text-destructive"
          >
            <span className="font-semibold">{resolveError(mutation.error).title}</span>
            <p>{resolveError(mutation.error).message}</p>
          </div>
        )}

        <DialogFooter className="flex-wrap justify-between gap-2">
          <Button
            type="button"
            data-testid="request-changes-cancel"
            variant="outline"
            disabled={pending}
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <div className="flex gap-2">
            <Button
              type="button"
              data-testid="request-changes-reassign"
              variant="secondary"
              disabled={pending}
              onClick={() => mutation.mutate({ task, decision: 'reassign', note })}
            >
              {pending ? 'Sending…' : 'Reassign'}
            </Button>
            <Button
              type="button"
              data-testid="request-changes-confirm"
              disabled={pending}
              onClick={() => {
                if (!showNoteError(note)) {
                  return; // T16 note guard — client-side, before any request
                }
                mutation.mutate({ task, decision: 'request_changes', note });
              }}
            >
              {pending ? 'Sending…' : 'Request changes'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
