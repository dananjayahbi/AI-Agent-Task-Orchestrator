/**
 * MT-4.8-02 — review panel (Section 13.2 composition): escalation reason
 * with the verbatim Section 8.4 code, the Section 9.4 rule table rendered
 * from persisted `policy_rule_results` (never recomputed client-side),
 * Section 10.5 evidence commands with exit codes, distinct no-report /
 * no-submission / error states (an empty "all pass" table is never
 * faked), the hosted WP-4.7 diff + WP-4.6 attachments embeds, and the
 * mount contract: the panel appears in the task detail only while the
 * task sits in `in_human_review`.
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ReviewPanel } from '@/components/review/review-panel';
import { TaskDetail } from '@/components/task/detail/task-detail';
import { REVIEW_REASONS, reviewReasonLabel } from '@/lib/review/review-reasons';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  type Route,
} from '../helpers/api';
import { makeAttachment, makeAuditReport, makeResolution } from '../helpers/task-detail';
import { patchBodyPayload, ruleRow, SINGLE_FILE_PATCH } from '../diff/fixtures';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

/** Section 9.4 rows: R5 fails with **no** persisted reason → mapping fills in. */
const RULE_ROWS = [
  ruleRow('R1', true),
  ruleRow('R2', false, 'scope_violation'),
  ruleRow('R3', true),
  ruleRow('R4', true),
  ruleRow('R5', false),
  ruleRow('R6', true),
  ruleRow('R7', true),
  ruleRow('R8', true),
  ruleRow('R9', true),
];

/** Section 10.5 evidence: exit codes, lint flag, plus an unknown field. */
const EVIDENCE = {
  commands: [
    { label: 'unit tests', command: 'npx vitest run', exit_code: 0, summary: '362 passed' },
    { label: 'lint', command: 'npx eslint .', exit_code: 1 },
  ],
  lint_clean: false,
  stats: { duration_ms: 8421 },
};

const REPORT = makeAuditReport({
  resolution_id: 'res-0002',
  policy_rule_results: RULE_ROWS,
  evidence: EVIDENCE,
  auditor_notes: 'Scope files outside web/ were touched.',
  confidence: 4,
  proposed_verdict: 'flag_risk',
  policy_decision: 'escalate',
});

const reviewTask = (overrides: Partial<ReturnType<typeof makeTask>> = {}) =>
  makeTask({ state: 'in_human_review', review_reason: 'test_failure', ...overrides });

function panelRoutes(
  options: {
    resolutions?: unknown[];
    reports?: unknown[];
    attachments?: unknown[];
    resolutionsError?: boolean;
  } = {},
): Route[] {
  return [
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
      respond: options.resolutionsError
        ? () => errorResponse('SERVER_ERROR', 500, 'orm traceback')
        : () => jsonResponse(pageOf(options.resolutions ?? [makeResolution()])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/audit-reports(\?|$)/,
      respond: () => jsonResponse(pageOf(options.reports ?? [REPORT])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf(options.attachments ?? [])),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/resolutions\/[^/]+\/patch(\?|$)/,
      respond: () => jsonResponse(patchBodyPayload(SINGLE_FILE_PATCH)),
    },
  ];
}

function renderPanel(task: ReturnType<typeof makeTask> = reviewTask()) {
  return renderWithQueryClient(
    <ReviewPanel pid={PID} taskId={TASK_ID} task={task} streamStatus="open" />,
  );
}

describe('ReviewPanel (MT-4.8-02)', () => {
  it('mounts in the task detail only while the task is in human review', async () => {
    installApi([
      ...panelRoutes(),
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
        respond: () => jsonResponse(reviewTask()),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => sseConnection().response,
      },
    ]);
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);

    await waitFor(() => expect(screen.getByTestId('review-panel')).toBeTruthy());
    expect(screen.getByTestId('review-panel').getAttribute('aria-label')).toBe('Review panel');
    expect(screen.getByTestId('review-reason-item').textContent).toContain('test_failure');
  });

  it('keeps the plain detail view when the task is not awaiting review', async () => {
    installApi([
      ...panelRoutes(),
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/checkpoints(\?|$)/,
        respond: () => jsonResponse(pageOf([])),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+(\?|$)/,
        respond: () => jsonResponse(makeTask({ state: 'pending', review_reason: null })),
      },
      {
        method: 'GET',
        match: /\/api\/v1\/events\/stream(\?|$)/,
        respond: () => sseConnection().response,
      },
    ]);
    renderWithQueryClient(<TaskDetail pid={PID} taskId={TASK_ID} />);

    await waitFor(() => expect(screen.getByTestId('task-detail')).toBeTruthy());
    expect(screen.queryByTestId('review-panel')).toBeNull();
  });

  it('renders every Section 9.4 rule outcome verbatim with fail reasons', async () => {
    installApi(panelRoutes());
    renderPanel();

    await waitFor(() => expect(screen.getByTestId('review-rule-table')).toBeTruthy());
    for (const rule of ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']) {
      expect(screen.getByTestId(`review-rule-row-${rule}`)).toBeTruthy();
    }
    // Persisted fail reason wins when the row carries one (R2)…
    expect(screen.getByTestId('review-rule-outcome-R2').textContent).toBe('Fail');
    expect(screen.getByTestId('review-rule-outcome-R2').getAttribute('data-passed')).toBe('false');
    const r2Reason = screen.getByTestId('review-rule-reason-R2').textContent ?? '';
    expect(r2Reason).toContain('Changes outside the target scope');
    expect(r2Reason).toContain('(scope_violation)');
    // …and the Section 9.4 mapping fills in when it does not (R5).
    expect(screen.getByTestId('review-rule-outcome-R5').textContent).toBe('Fail');
    const r5Reason = screen.getByTestId('review-rule-reason-R5').textContent ?? '';
    expect(r5Reason).toContain('Sensitive config changed');
    expect(r5Reason).toContain('(sensitive_config_changed)');
    // Passing rows carry no reason cell.
    expect(screen.getByTestId('review-rule-outcome-R1').textContent).toBe('Pass');
    expect(screen.getByTestId('review-rule-outcome-R1').getAttribute('data-passed')).toBe('true');
    expect(screen.queryByTestId('review-rule-reason-R1')).toBeNull();
  });

  it('renders evidence commands with exit codes and collapses unknown fields', async () => {
    installApi(panelRoutes());
    renderPanel();

    await waitFor(() => expect(screen.getByTestId('review-evidence')).toBeTruthy());
    expect(screen.getByTestId('review-evidence-label-0').textContent).toBe('unit tests');
    expect(screen.getByTestId('review-evidence-exit-0').textContent).toBe('exit 0');
    expect(screen.getByTestId('review-evidence-label-1').textContent).toBe('lint');
    expect(screen.getByTestId('review-evidence-exit-1').textContent).toBe('exit 1');
    expect(screen.getByTestId('review-evidence-lint').textContent).toContain('No');
    // Section 10.5-known fields render inline; the rest stay visible but collapsed.
    const extra = screen.getByTestId('review-evidence-extra');
    expect(extra.textContent).toContain('duration_ms');
  });

  it('renders the submission summary and auditor report fields', async () => {
    installApi(panelRoutes());
    renderPanel();

    await waitFor(() => expect(screen.getByTestId('review-summary')).toBeTruthy());
    const summary = screen.getByTestId('review-summary').textContent ?? '';
    expect(summary).toContain('Attempt 2');
    expect(summary).toContain('feat/login @ abcdef123456');
    expect(summary).toContain('Implemented the login form');
    expect(screen.getByTestId('review-summary-diff').textContent).toContain('+120');
    expect(screen.getByTestId('review-audit-notes').textContent).toContain(
      'Scope files outside web/ were touched.',
    );
    expect(screen.getByTestId('review-audit-confidence').textContent).toBe('4/5');
    expect(screen.getByTestId('review-audit-verdict').textContent).toBe('flag_risk');
    expect(screen.getByTestId('review-audit-policy').textContent).toBe('escalate');
  });

  it('renders all twelve Section 8.4 reasons with verbatim codes', async () => {
    installApi(panelRoutes());
    for (const reason of REVIEW_REASONS) {
      const view = renderPanel(reviewTask({ review_reason: reason }));
      const item = screen.getByTestId('review-reason-item');
      expect(item.textContent).toContain(reviewReasonLabel(reason));
      expect(item.textContent).toContain(`(${reason})`);
      view.unmount();
    }
  });

  it('degrades to summary without a rule table when no audit report exists', async () => {
    installApi(panelRoutes({ reports: [] }));
    renderPanel();

    await waitFor(() => expect(screen.getByTestId('review-no-report')).toBeTruthy());
    expect(screen.getByTestId('review-summary')).toBeTruthy();
    // Never an empty "all pass" table (MT risk note; Section 8.5 path).
    expect(screen.queryByTestId('review-rule-table')).toBeNull();
    expect(screen.queryByTestId('review-no-rule-results')).toBeNull();
    expect(screen.getByTestId('review-no-report').textContent).toContain('No audit report');
  });

  it('degrades to reason + note for a pre-audit escalation with no submission', async () => {
    installApi(panelRoutes({ resolutions: [] }));
    renderPanel(reviewTask({ review_reason: 'retry_exhausted' }));

    await waitFor(() => expect(screen.getByTestId('review-no-submission')).toBeTruthy());
    expect(screen.getByTestId('review-reason-item').textContent).toContain('(retry_exhausted)');
    expect(screen.queryByTestId('review-rule-table')).toBeNull();
    expect(screen.queryByTestId('review-summary')).toBeNull();
    // Diff section needs a resolution; there is none to view.
    expect(screen.queryByTestId('review-diff-toggle')).toBeNull();
  });

  it('shows catalog-only error copy when submissions fail to load', async () => {
    installApi(panelRoutes({ resolutionsError: true }));
    renderPanel();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(alert.textContent).not.toContain('orm traceback');
    expect(screen.queryByTestId('review-rule-table')).toBeNull();
  });

  it('embeds the hosted diff panel and attachment viewer instead of re-implementing', async () => {
    const { calls } = installApi(panelRoutes({ attachments: [makeAttachment()] }));
    renderPanel();

    await waitFor(() => expect(screen.getByTestId('attachment-row')).toBeTruthy());
    expect(screen.getByTestId('review-attachments')).toBeTruthy();

    fireEvent.click(screen.getByTestId('review-diff-toggle'));
    await waitFor(() => expect(screen.getByTestId('review-diff')).toBeTruthy());
    expect(screen.getByTestId('review-diff-toggle').getAttribute('aria-expanded')).toBe('true');
    expect(calls.filter((call) => call.pathname.includes('/patch'))).toHaveLength(1);
  });
});
