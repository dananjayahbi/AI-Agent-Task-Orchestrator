/**
 * Event catalog gate (MT-4.3-04; parent plan Section 9.6 — the catalog is
 * a closed set; Section 20.4 item 6).
 *
 * The generated `EventEnvelopeTypeEnum` is the type-level truth; this
 * module mirrors it as a runtime list so the stream can ignore anything
 * the server should never send. The coverage assertion below fails the
 * build when the schema adds a catalog type — a new event must be a
 * deliberate decision here, never silently forwarded (drift discipline,
 * same pattern as lib/board/states.ts).
 */
import type { EventEnvelopeTypeEnum } from '@/lib/api/generated/types.gen';

/** Section 9.6 catalog, in plan order. */
export const EVENT_CATALOG = [
  'project.created',
  'project.updated',
  'task.created',
  'task.updated',
  'task.transitioned',
  'task.claimed',
  'task.released',
  'task.checkpoint',
  'task.lease_expiring',
  'task.lease_expired',
  'attachment.processing',
  'attachment.ready',
  'attachment.failed',
  'audit.claimed',
  'audit.passed',
  'audit.escalated',
  'review.requested',
  'review.decided',
  'merge.started',
  'merge.succeeded',
  'merge.failed',
  'agent.session_started',
  'agent.session_ended',
  'system.alert',
] as const satisfies readonly EventEnvelopeTypeEnum[];

type CatalogCoverage =
  Exclude<EventEnvelopeTypeEnum, (typeof EVENT_CATALOG)[number]> extends never
    ? (typeof EVENT_CATALOG)[number] extends EventEnvelopeTypeEnum
      ? true
      : never
    : never;
const _coverage: CatalogCoverage = true;
void _coverage;

const CATALOG_SET: ReadonlySet<string> = new Set(EVENT_CATALOG);

/** Runtime gate: only Section 9.6 catalog types pass; anything else is ignored. */
export function isCatalogEventType(value: unknown): value is EventEnvelopeTypeEnum {
  return typeof value === 'string' && CATALOG_SET.has(value);
}
