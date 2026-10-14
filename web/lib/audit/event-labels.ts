/**
 * Friendly display labels for the Section 9.6 event catalog (MT-4.10-01;
 * ADR-010 — canonical values are separate from display labels and are
 * never replaced by them).
 *
 * Exhaustive by construction: keyed as `Record<EventEnvelopeTypeEnum,
 * string>`, so a future catalog type is a compile error until its label
 * is chosen here. Server types outside the catalog (forward types) have
 * no label — the viewer renders them raw (Section 20.4 item 6; the
 * client never fabricates catalog entries).
 */
import type { EventEnvelopeTypeEnum } from '@/lib/api/generated/types.gen';

export const EVENT_LABELS: Record<EventEnvelopeTypeEnum, string> = {
  'project.created': 'Project created',
  'project.updated': 'Project updated',
  'task.created': 'Task created',
  'task.updated': 'Task updated',
  'task.transitioned': 'Task transitioned',
  'task.claimed': 'Task claimed',
  'task.released': 'Task released',
  'task.checkpoint': 'Checkpoint',
  'task.lease_expiring': 'Lease expiring',
  'task.lease_expired': 'Lease expired',
  'attachment.processing': 'Attachment processing',
  'attachment.ready': 'Attachment ready',
  'attachment.failed': 'Attachment failed',
  'audit.claimed': 'Audit claimed',
  'audit.passed': 'Audit passed',
  'audit.escalated': 'Audit escalated',
  'review.requested': 'Review requested',
  'review.decided': 'Review decided',
  'merge.started': 'Merge started',
  'merge.succeeded': 'Merge succeeded',
  'merge.failed': 'Merge failed',
  'agent.session_started': 'Agent session started',
  'agent.session_ended': 'Agent session ended',
  'system.alert': 'System alert',
};

/** null = not in the catalog → the viewer shows the raw type only. */
export function eventLabel(type: string): string | null {
  return Object.prototype.hasOwnProperty.call(EVENT_LABELS, type)
    ? EVENT_LABELS[type as EventEnvelopeTypeEnum]
    : null;
}
