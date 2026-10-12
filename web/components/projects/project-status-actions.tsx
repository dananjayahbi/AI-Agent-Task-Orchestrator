'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FormBanner } from '@/components/projects/form-field';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { callApi, partialUpdateProject, type Project } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import { queryKeys } from '@/lib/queries/keys';

type Status = Project['active_status'];

/**
 * Transitions the server permits for each state (FR-PRJ-04 — pause/resume/
 * archive; projects are never deleted). Only these are offered; the server
 * re-validates regardless. Archive is destructive-flavoured and always
 * double-confirms (MT-4.2-02).
 */
const ACTIONS: Record<
  Status,
  Array<{
    to: Status;
    label: string;
    confirmTitle: string;
    confirmBody: string;
    destructive?: boolean;
  }>
> = {
  active: [
    {
      to: 'paused',
      label: 'Pause',
      confirmTitle: 'Pause this project?',
      confirmBody:
        'Pausing stops agents from claiming new tasks in this project. Existing work is unaffected.',
    },
    {
      to: 'archived',
      label: 'Archive',
      confirmTitle: 'Archive this project?',
      confirmBody:
        'Archiving takes the project out of day-to-day use. You can restore it later from Project settings.',
      destructive: true,
    },
  ],
  paused: [
    {
      to: 'active',
      label: 'Resume',
      confirmTitle: 'Resume this project?',
      confirmBody: 'Resuming lets agents claim tasks in this project again.',
    },
    {
      to: 'archived',
      label: 'Archive',
      confirmTitle: 'Archive this project?',
      confirmBody:
        'Archiving takes the project out of day-to-day use. You can restore it later from Project settings.',
      destructive: true,
    },
  ],
  archived: [
    {
      to: 'active',
      label: 'Restore',
      confirmTitle: 'Restore this project?',
      confirmBody: 'Restoring makes the project active again so agents can claim its tasks.',
    },
  ],
};

/** Status transitions with confirmation dialogs (MT-4.2-02). */
export function ProjectStatusActions({ project }: { project: Project }) {
  const queryClient = useQueryClient();
  const [pending, setPending] = useState<(typeof ACTIONS)[Status][number] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const transition = useMutation({
    mutationFn: (status: Status) =>
      callApi(partialUpdateProject({ path: { pid: project.id }, body: { active_status: status } })),
    onSuccess: () => {
      setPending(null);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(project.id) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
    onError: (caught) => {
      // Server rejection surfaces as a structured, friendly error — and the
      // dialog stays open so the attempted action is visible.
      setError(resolveError(caught).message);
    },
  });

  return (
    <div className="flex flex-wrap items-center gap-2">
      {ACTIONS[project.active_status].map((action) => (
        <Button
          key={`${action.to}`}
          variant={action.destructive === true ? 'destructive' : 'outline'}
          size="sm"
          onClick={() => {
            setError(null);
            setPending(action);
          }}
        >
          {action.label}
        </Button>
      ))}

      <Dialog
        open={pending !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPending(null);
            setError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{pending?.confirmTitle ?? ''}</DialogTitle>
            <DialogDescription>{pending?.confirmBody ?? ''}</DialogDescription>
          </DialogHeader>
          {error !== null && <FormBanner variant="error">{error}</FormBanner>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>
              Cancel
            </Button>
            <Button
              variant={pending?.destructive === true ? 'destructive' : 'default'}
              disabled={transition.isPending}
              onClick={() => {
                if (pending !== null) transition.mutate(pending.to);
              }}
            >
              {transition.isPending ? 'Applying…' : 'Confirm'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
