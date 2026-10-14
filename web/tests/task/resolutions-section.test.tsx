/**
 * MT-4.6-03 (available part) — resolutions history: one entry per
 * submission attempt (Section 7.2 fields, newest attempt first), the
 * backend's authoritative diff stats (Section 9.7 — never recomputed
 * client-side), audit-report pairing by resolution id (Section 8.5
 * auditor-less flows render without one), fetch-on-expand
 * (Section 13.3/13.4), and `latest_feedback` visibility (WP-3.6 field).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ResolutionsSection } from '@/components/task/detail/resolutions-section';
import {
  errorResponse,
  installApi,
  jsonResponse,
  pageOf,
  renderWithQueryClient,
} from '../helpers/api';
import { makeAuditReport, makeResolution } from '../helpers/task-detail';

afterEach(() => {
  vi.unstubAllGlobals();
});

const PID = 'PID00001';
const TASK_ID = 'PID00001-T001';

function sectionHarness(resolutions: unknown[], reports: unknown[] = []) {
  const { calls } = installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
      respond: () => jsonResponse(pageOf(resolutions)),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/[^/]+\/audit-reports(\?|$)/,
      respond: () => jsonResponse(pageOf(reports)),
    },
  ]);
  return { calls };
}

const resolutionCalls = (calls: Array<{ pathname: string }>) =>
  calls.filter((call) => call.pathname.endsWith('/resolutions'));
const reportCalls = (calls: Array<{ pathname: string }>) =>
  calls.filter((call) => call.pathname.endsWith('/audit-reports'));

describe('ResolutionsSection (MT-4.6-03)', () => {
  it('fetches on expand only — nothing loads while collapsed (Section 13.3)', async () => {
    const { calls } = sectionHarness([makeResolution()]);
    renderWithQueryClient(<ResolutionsSection pid={PID} taskId={TASK_ID} />);
    // Collapsed: no attempt history pulled (RISK-13 first-load guard).
    expect(resolutionCalls(calls)).toHaveLength(0);
    expect(reportCalls(calls)).toHaveLength(0);
    expect(screen.getByTestId('resolutions-toggle').getAttribute('aria-expanded')).toBe('false');

    fireEvent.click(screen.getByTestId('resolutions-toggle'));

    await waitFor(() => expect(screen.getByTestId('resolution-entry')).toBeTruthy());
    expect(resolutionCalls(calls)).toHaveLength(1);
    expect(reportCalls(calls)).toHaveLength(1);
  });

  it('renders one entry per attempt, newest first, with Section 7.2 fields', async () => {
    sectionHarness([
      makeResolution({
        id: 'res-1',
        attempt_number: 1,
        branch_name: 'feat/login-take-1',
        commit_sha: '111111111111aaaaaaaa',
        execution_summary: 'First attempt',
        submitted_at: '2026-10-01T09:00:00Z',
      }),
      makeResolution({
        id: 'res-2',
        attempt_number: 2,
        branch_name: 'feat/login',
        commit_sha: 'abcdef1234567890abcdef12', // pragma: allowlist secret
        execution_summary: 'Second attempt after review',
        diff_summary: { files: 3, insertions: 120, deletions: 4 },
        requires_human_attention: true,
        risk_justification: 'Touches the auth middleware',
        submitted_at: '2026-10-01T10:05:00Z',
      }),
    ]);
    renderWithQueryClient(<ResolutionsSection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('resolutions-toggle'));

    await waitFor(() => expect(screen.getAllByTestId('resolution-entry')).toHaveLength(2));
    const entries = screen.getAllByTestId('resolution-entry');
    // Newest attempt first.
    expect(entries[0].getAttribute('data-attempt')).toBe('2');
    expect(entries[1].getAttribute('data-attempt')).toBe('1');
    // Section 7.2 fields surface verbatim.
    expect(within(entries[0]).getByTestId('resolution-branch').textContent).toBe('feat/login');
    expect(within(entries[0]).getByTestId('resolution-commit').textContent).toBe('abcdef123456'); // pragma: allowlist secret
    expect(within(entries[0]).getByTestId('resolution-summary').textContent).toBe(
      'Second attempt after review',
    );
    // Diff stats are the backend's authoritative values (Section 9.7).
    const stats = within(entries[0]).getByTestId('resolution-diff-stats');
    expect(stats.getAttribute('data-files')).toBe('3');
    expect(stats.textContent).toBe('3 files · +120 · −4');
    // Coder self-flag (T8 guard input).
    expect(entries[0].textContent).toContain('Coder flagged for human attention');
    expect(within(entries[0]).getByTestId('resolution-risk').textContent).toBe(
      'Touches the auth middleware',
    );
    // Attempt without a report degrades gracefully (Section 8.5).
    expect(entries[1].textContent).toContain('No audit report for this attempt.');
  });

  it('pairs the audit report to its resolution and renders the verdict summary', async () => {
    sectionHarness(
      [makeResolution({ id: 'res-2', attempt_number: 2 })],
      [
        makeAuditReport({
          resolution_id: 'res-2',
          proposed_verdict: 'flag_risk',
          confidence: 3,
          policy_decision: 'escalate',
          auditor_notes: 'Diff touches migrations.',
        }),
      ],
    );
    renderWithQueryClient(<ResolutionsSection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('resolutions-toggle'));

    await waitFor(() => expect(screen.getByTestId('resolution-audit-report')).toBeTruthy());
    expect(screen.getByTestId('audit-verdict').textContent).toBe('Flagged risk');
    expect(screen.getByTestId('audit-confidence').textContent).toBe('Confidence 3/5');
    expect(screen.getByTestId('audit-policy-decision').textContent).toBe('Escalated to review');
    expect(screen.getByTestId('audit-notes').textContent).toBe('Diff touches migrations.');
  });

  it('renders the empty state when the task has no submissions', async () => {
    sectionHarness([]);
    renderWithQueryClient(<ResolutionsSection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('resolutions-toggle'));
    await waitFor(() => expect(screen.getByText('No submissions yet')).toBeTruthy());
  });

  it('maps resolutions errors to catalog copy only', async () => {
    installApi([
      {
        method: 'GET',
        match: /\/api\/v1\/tasks\/[^/]+\/resolutions(\?|$)/,
        respond: () => errorResponse('SERVER_ERROR', 500, 'orm traceback'),
      },
    ]);
    renderWithQueryClient(<ResolutionsSection pid={PID} taskId={TASK_ID} />);
    fireEvent.click(screen.getByTestId('resolutions-toggle'));
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('Something went wrong');
    expect(alert.textContent).not.toContain('orm traceback');
  });
});
