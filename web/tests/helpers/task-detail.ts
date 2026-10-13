/**
 * WP-4.6 task-detail fixtures (MT-4.6-01…04): one complete contract-matching
 * factory per Section 7.2 entity the detail view renders, mirroring the
 * documented field sets from the generated types (checkpoints, attachments,
 * attachment content, resolutions, audit reports).
 */
import type {
  Attachment,
  AttachmentContent,
  AuditReport,
  Checkpoint,
  Resolution,
} from '@/lib/api/generated/types.gen';

/** One stored checkpoint (Section 7.2 Task Checkpoint fields). */
export function makeCheckpoint(overrides: Partial<Checkpoint> = {}): Checkpoint {
  return {
    id: 'chk-0001',
    task_id: 'PID00001-T001',
    attempt_number: 1,
    session_id: 'sess-1',
    timestamp: '2026-10-01T10:00:00Z',
    message: 'Started work',
    percent: 40,
    token_usage: null,
    kind: 'progress',
    ...overrides,
  };
}

/** One attachment descriptor (FR-ATT-03/07 field set). */
export function makeAttachment(overrides: Partial<Attachment> = {}): Attachment {
  return {
    id: 'att-0001',
    task_id: 'PID00001-T001',
    filename: 'diagram.png',
    mime_type: 'image/png',
    size: 2048,
    is_image: true,
    processing_status: 'ready',
    failure_reason: null,
    token_count: 120,
    short_description: 'Architecture diagram',
    created_at: '2026-10-01T09:30:00Z',
    ...overrides,
  };
}

/** One content-endpoint page (Section 9.5 retrieval body). */
export function makeAttachmentContent(
  overrides: Partial<AttachmentContent> = {},
): AttachmentContent {
  return {
    attachment_id: 'att-0001',
    format: 'image_base64',
    content: null,
    description: null,
    image_base64: null,
    media_type: null,
    page_number: null,
    total_pages: null,
    token_count: null,
    ...overrides,
  };
}

/** One submission attempt (Section 7.2 Task Resolution fields). */
export function makeResolution(overrides: Partial<Resolution> = {}): Resolution {
  return {
    id: 'res-0002',
    task_id: 'PID00001-T001',
    attempt_number: 2,
    branch_name: 'feat/login',
    commit_sha: 'abcdef1234567890abcdef12', // pragma: allowlist secret
    execution_summary: 'Implemented the login form and wired the submit handler.',
    diff_summary: { files: 3, insertions: 120, deletions: 4 },
    changed_files: ['web/login.tsx'],
    requires_human_attention: false,
    risk_justification: '',
    submitted_by_session: 'sess-1',
    submitted_at: '2026-10-01T10:05:00Z',
    ...overrides,
  };
}

/** One stored audit report (Section 7.2 Audit Report fields). */
export function makeAuditReport(overrides: Partial<AuditReport> = {}): AuditReport {
  return {
    id: 'aud-0001',
    task_id: 'PID00001-T001',
    resolution_id: 'res-0002',
    auditor_session_id: 'sess-auditor',
    evidence: {},
    confidence: 4,
    auditor_notes: 'Tests pass; scope respected.',
    proposed_verdict: 'pass',
    policy_decision: 'approve',
    policy_rule_results: null,
    policy_engine_version: null,
    created_at: '2026-10-01T10:10:00Z',
    ...overrides,
  };
}
