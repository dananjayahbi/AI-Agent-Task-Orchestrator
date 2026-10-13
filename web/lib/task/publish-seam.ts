/**
 * Publish transport seam (MT-4.5-06; Section 9.2 `POST /tasks/{id}/transition`).
 *
 * The transition endpoint is **not yet in `schemas/openapi.yaml`** (an
 * open question tracked in the WP changelog), so the typed client has no
 * operation for it and NFR-11 forbids a hand-written path. This module
 * fixes the seam shape instead — the exact Section 8.2 T2 request the
 * eventual consumer will send — following the WP-4.4 precedent (allowed
 * moves route to an explicit notice until the consumer lands):
 *
 *  - `version` is the CAS token the client saw (Section 8.2: "the UI
 *    sends the `version` it saw"); a stale value answers
 *    `VERSION_CONFLICT`;
 *  - `override` is FR-ATT-07's "explicitly overridden" flag — true only
 *    after the operator consciously chooses publish-anyway for non-ready
 *    attachments;
 *  - with no consumer wired, publishing shows an explicit unavailable
 *    notice — never a silent no-op and never a cache mutation.
 */

export type PublishRequest = {
  taskId: string;
  version: number;
  /** FR-ATT-07: true only via the explicit override choice. */
  override: boolean;
};

/** The eventual consumer sends `POST /tasks/{id}/transition` (T2 publish). */
export type PublishTransport = (request: PublishRequest) => Promise<void>;

/** Fallback copy while the endpoint is absent from the schema (stable — tests assert it). */
export function publishUnavailableNotice(taskId: string): string {
  return (
    `Publish is validated for ${taskId}, but sending transitions is not available yet ` +
    '(`POST /tasks/{id}/transition` is not in the published schema) — the task stays in Draft.'
  );
}
