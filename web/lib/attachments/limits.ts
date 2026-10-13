/**
 * Client pre-checks for attachment uploads (MT-4.5-05; parent plan
 * Section 9.5 "Limits and safety").
 *
 * A line-for-line mirror of the backend defaults (WP-1.11
 * `apps/attachments/validation.py`): 25 MB per file, 10 attachments per
 * task, 100 MB total, and the exact Section 9.5 type allowlist. These
 * checks are UX only — the server re-validates everything, sniffs MIME
 * from content and remains the authority (MT risk note: never disable a
 * server error the client happened to allow).
 */

export const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024; // 25 MB
export const MAX_ATTACHMENTS_PER_TASK = 10;
export const MAX_TOTAL_BYTES = 100 * 1024 * 1024; // 100 MB

/** Section 9.5 allowlist, verbatim (DOCX uses its registered MIME type). */
export const ALLOWED_ATTACHMENT_MIME_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/markdown',
  'text/plain',
] as const;

/** Human label list for the dropzone hint. */
export const ALLOWED_ATTACHMENT_LABELS = 'PNG, JPEG, WebP, PDF, DOCX, Markdown, plain text';

export type PrecheckResult = { ok: true } | { ok: false; message: string };

function megabytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * One file's Section 9.5 pre-check against the task's current usage.
 * An empty/unknown browser MIME type is left to the server's content
 * sniffing (the client can only guess from `File.type`; guessing wrong
 * must not block a valid upload).
 */
export function precheckAttachment(
  file: { name: string; size: number; type: string },
  context: { existingCount: number; existingTotalBytes: number; queuedTotalBytes: number },
): PrecheckResult {
  if (file.size === 0) {
    return { ok: false, message: 'The file is empty — pick a file with content.' };
  }
  if (file.size > MAX_ATTACHMENT_BYTES) {
    return {
      ok: false,
      message: `The file is ${megabytes(file.size)} — the per-file limit is ${megabytes(MAX_ATTACHMENT_BYTES)}.`,
    };
  }
  if (context.existingCount >= MAX_ATTACHMENTS_PER_TASK) {
    return {
      ok: false,
      message: `This task already has the maximum of ${MAX_ATTACHMENTS_PER_TASK} attachments — remove one before adding another.`,
    };
  }
  const projected = context.existingTotalBytes + context.queuedTotalBytes + file.size;
  if (projected > MAX_TOTAL_BYTES) {
    return {
      ok: false,
      message: `The file would push the task past the ${megabytes(MAX_TOTAL_BYTES)} total attachment limit.`,
    };
  }
  const declared = file.type.trim().toLowerCase();
  if (declared !== '' && !(ALLOWED_ATTACHMENT_MIME_TYPES as readonly string[]).includes(declared)) {
    return {
      ok: false,
      message: `Files of type "${declared}" aren't supported — accepted: ${ALLOWED_ATTACHMENT_LABELS}.`,
    };
  }
  return { ok: true };
}
