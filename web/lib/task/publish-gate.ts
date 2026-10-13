/**
 * Publish gate (MT-4.5-06; parent plan Section 8.2 T2 — "Required fields
 * valid; attachments `ready` (or override); dependencies exist").
 *
 * A pure evaluator over what the client currently knows, mirroring the
 * server's T2 guards (the server stays the authority — this gate is UX):
 *
 *  - **required fields valid** — WP-1.5's recorded reading: the task has
 *    a non-blank title (the only plan-required field);
 *  - **attachments ready (or override)** — every attached file must
 *    report `ready`; `uploaded`/`processing` block with per-file status,
 *    `failed` blocks with its pipeline reason. FR-ATT-07's explicit
 *    override may clear *attachment* blockers only — never required
 *    fields or dependencies, and never silently (the UI demands a
 *    conscious choice);
 *  - **dependencies exist** — the WP-1.5 recorded reading: every
 *    dependency exists **and is completed** (shared with T4);
 *  - **unsaved form changes** block publish — T2 guards run against the
 *    *saved* row, so the operator saves first; publishing stale edits
 *    would surprise everyone.
 *
 * Dependency rows can be `unknown` while their lookup is in flight; the
 * gate treats unknown as not-yet-publishable rather than guessing.
 */
import type { Attachment } from '@/lib/api/generated/types.gen';

export type DependencyGateEntry = {
  id: string;
  status: 'completed' | 'incomplete' | 'unknown';
};

export type PublishBlocker =
  | { kind: 'not_draft' }
  | { kind: 'unsaved_changes' }
  | { kind: 'missing_title' }
  | { kind: 'attachments_loading' }
  | { kind: 'attachments_pending'; pending: number }
  | { kind: 'attachments_failed'; reasons: string[] }
  | { kind: 'dependencies_unknown' }
  | { kind: 'dependencies_unmet'; ids: string[] };

/** Attachment blockers are the only ones FR-ATT-07's override clears. */
function isAttachmentBlocker(blocker: PublishBlocker): boolean {
  return (
    blocker.kind === 'attachments_loading' ||
    blocker.kind === 'attachments_pending' ||
    blocker.kind === 'attachments_failed'
  );
}

export type PublishGate = {
  blockers: PublishBlocker[];
  /** True when every blocker is attachment-readiness (override territory). */
  overrideCovers: boolean;
  canPublish: boolean; // with no blockers at all
};

export function evaluatePublishGate(input: {
  state: string;
  dirty: boolean;
  titleValid: boolean;
  /** `undefined` = the attachments list has not loaded yet. */
  attachments: readonly Attachment[] | undefined;
  /** Mirrors the *saved* `depends_on` set (post-save form values). */
  dependencies: readonly DependencyGateEntry[];
}): PublishGate {
  const blockers: PublishBlocker[] = [];

  if (input.state !== 'draft') blockers.push({ kind: 'not_draft' });
  if (input.dirty) blockers.push({ kind: 'unsaved_changes' });
  if (!input.titleValid) blockers.push({ kind: 'missing_title' });

  if (input.attachments === undefined) {
    blockers.push({ kind: 'attachments_loading' });
  } else {
    const pending = input.attachments.filter(
      (row) => row.processing_status === 'uploaded' || row.processing_status === 'processing',
    );
    if (pending.length > 0) {
      blockers.push({ kind: 'attachments_pending', pending: pending.length });
    }
    const failed = input.attachments.filter((row) => row.processing_status === 'failed');
    if (failed.length > 0) {
      blockers.push({
        kind: 'attachments_failed',
        reasons: failed.map(
          (row) => `${row.filename}: ${row.failure_reason ?? 'processing failed'}`,
        ),
      });
    }
  }

  if (input.dependencies.some((dep) => dep.status === 'unknown')) {
    blockers.push({ kind: 'dependencies_unknown' });
  }
  const unmet = input.dependencies
    .filter((dep) => dep.status === 'incomplete')
    .map((dep) => dep.id);
  if (unmet.length > 0) {
    blockers.push({ kind: 'dependencies_unmet', ids: unmet });
  }

  return {
    blockers,
    overrideCovers: blockers.length > 0 && blockers.every(isAttachmentBlocker),
    canPublish: blockers.length === 0,
  };
}

/** Operator-facing copy per blocker (Section 13.3 friendly voice). */
export function publishBlockerMessage(blocker: PublishBlocker): string {
  switch (blocker.kind) {
    case 'not_draft':
      return 'Only draft tasks can be published (T2).';
    case 'unsaved_changes':
      return 'Save your changes first — publishing applies to the saved task.';
    case 'missing_title':
      return 'A title is required before publishing (T2 guard).';
    case 'attachments_loading':
      return 'Attachment statuses are still loading.';
    case 'attachments_pending':
      return `${blocker.pending} attachment${blocker.pending === 1 ? ' is' : 's are'} still processing — publish becomes available when all report ready.`;
    case 'attachments_failed':
      return `Failed attachments block publish — remove them, or choose the explicit override. ${blocker.reasons.join('; ')}`;
    case 'dependencies_unknown':
      return 'Dependency states are still loading.';
    case 'dependencies_unmet':
      return `Dependencies must be completed before publishing: ${blocker.ids.join(', ')}.`;
  }
}
