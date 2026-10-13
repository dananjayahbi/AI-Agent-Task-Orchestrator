/**
 * MT-4.3-02 — task card: the Section 13.2 element list, the Section 8.6
 * stalled definition, priority chips (Section 7.2) and graceful
 * claimed/percent-less rendering.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TaskCard } from '@/components/board/task-card';
import { makeTask } from '../helpers/api';

/** Deterministic clock: 2026-10-01T12:00:00Z. */
const NOW = Date.parse('2026-10-01T12:00:00Z');

describe('TaskCard (MT-4.3-02)', () => {
  it('renders all seven Section 13.2 elements from fixture data', () => {
    render(
      <TaskCard
        nowMs={NOW}
        percent={42}
        attachmentCount={3}
        task={makeTask({
          id: 'PID00001-T007',
          title: 'Wire the board',
          priority: 'high',
          state: 'in_progress',
          worker_agent_id: 'claude-code-session-98b2',
          lease_acquired_at: '2026-10-01T11:30:00Z',
          lease_expires_at: '2026-10-01T12:15:00Z', // 15m remaining
          last_checkpoint_at: '2026-10-01T11:58:00Z', // healthy: recent progress
        })}
      />,
    );

    expect(screen.getByTestId('task-card-id').textContent).toBe('PID00001-T007');
    expect(screen.getByTestId('task-card-title').textContent).toBe('Wire the board');
    expect(screen.getByTestId('priority-chip-high').textContent).toBe('high');
    const worker = screen.getByTestId('task-card-worker');
    expect(worker.textContent).toContain('claude-code-session-98b2');
    expect(screen.getByTestId('task-card-lease').textContent).toBe('15m 00s');
    expect(screen.getByTestId('task-card-progress-label').textContent).toBe('42%');
    expect(screen.getByTestId('task-card-progress').getAttribute('aria-valuenow')).toBe('42');
    expect(screen.getByTestId('task-card-attachments').textContent).toBe('3 attachments');
    // No stalled/escalation/merge marker for a healthy claimed task.
    expect(screen.queryByTestId('task-card-stalled')).toBeNull();
    expect(screen.queryByTestId('task-card-escalation')).toBeNull();
    expect(screen.queryByTestId('task-card-merge-badge')).toBeNull();
  });

  it('covers exactly the four Section 7.2 priorities with themed chips', () => {
    for (const priority of ['urgent', 'high', 'medium', 'low'] as const) {
      render(<TaskCard nowMs={NOW} task={makeTask({ priority })} />);
      const chip = screen.getByTestId(`priority-chip-${priority}`);
      expect(chip.textContent).toBe(priority);
      expect(chip.getAttribute('aria-label')).toBe(`Priority ${priority}`);
    }
  });

  it('shows no worker badge for unclaimed tasks', () => {
    render(<TaskCard nowMs={NOW} task={makeTask({ state: 'pending', worker_agent_id: null })} />);
    expect(screen.queryByTestId('task-card-worker')).toBeNull();
    expect(screen.getByTestId('task-card')).toBeTruthy();
  });

  it('renders an explicit unknown progress state — never 0 % for a missing report', () => {
    render(<TaskCard nowMs={NOW} percent={null} task={makeTask()} />);
    const bar = screen.getByTestId('task-card-progress');
    expect(bar.getAttribute('data-percent')).toBe('unknown');
    expect(bar.getAttribute('aria-valuenow')).toBeNull();
    expect(screen.getByTestId('task-card-progress-label').textContent).toBe('Progress unknown');
    expect(screen.getByTestId('task-card-attachments').textContent).toBe('– attachments');
  });

  it('marks a stalled task per Section 8.6: no checkpoint within the policy window, lease valid', () => {
    render(
      <TaskCard
        nowMs={NOW}
        stalledAfterMinutes={20}
        task={makeTask({
          state: 'in_progress',
          worker_agent_id: 'coder-1',
          lease_acquired_at: '2026-10-01T11:00:00Z',
          lease_expires_at: '2026-10-01T12:30:00Z', // still valid
          last_checkpoint_at: '2026-10-01T11:20:00Z', // 40 min ago > 20 min window
        })}
      />,
    );
    expect(screen.getByTestId('task-card-stalled')).toBeTruthy();
  });

  it('does not mark a task stalled when a recent checkpoint arrived inside the window', () => {
    render(
      <TaskCard
        nowMs={NOW}
        stalledAfterMinutes={20}
        task={makeTask({
          state: 'in_progress',
          worker_agent_id: 'coder-1',
          lease_expires_at: '2026-10-01T12:30:00Z',
          last_checkpoint_at: '2026-10-01T11:55:00Z', // 5 min ago
        })}
      />,
    );
    expect(screen.queryByTestId('task-card-stalled')).toBeNull();
  });

  it('does not mark a task stalled once the lease is no longer valid (T5 territory)', () => {
    render(
      <TaskCard
        nowMs={NOW}
        stalledAfterMinutes={20}
        task={makeTask({
          state: 'in_progress',
          worker_agent_id: 'coder-1',
          lease_expires_at: '2026-10-01T11:50:00Z', // expired 10 min ago
          last_checkpoint_at: null,
        })}
      />,
    );
    expect(screen.queryByTestId('task-card-stalled')).toBeNull();
  });

  it('measures the never-checkpointed window from the claim time', () => {
    render(
      <TaskCard
        nowMs={NOW}
        stalledAfterMinutes={20}
        task={makeTask({
          state: 'in_progress',
          worker_agent_id: 'coder-1',
          lease_acquired_at: '2026-10-01T11:30:00Z',
          lease_expires_at: '2026-10-01T12:30:00Z',
          last_checkpoint_at: null, // claimed 30 min ago, silent since
        })}
      />,
    );
    expect(screen.getByTestId('task-card-stalled')).toBeTruthy();
  });

  it('surfaces the escalation marker with the review reason accessibly (full panel is WP-4.8)', () => {
    render(
      <TaskCard
        nowMs={NOW}
        task={makeTask({ state: 'in_human_review', review_reason: 'scope_violation' })}
      />,
    );
    const marker = screen.getByTestId('task-card-escalation');
    expect(marker.getAttribute('aria-label')).toBe('Needs review: scope_violation');
    expect(marker.getAttribute('title')).toBe('scope_violation');
  });

  it('formats long lease countdowns in hours and expired leases as "expired"', () => {
    const { rerender } = render(
      <TaskCard
        nowMs={NOW}
        task={makeTask({
          state: 'in_progress',
          worker_agent_id: 'coder-1',
          lease_expires_at: '2026-10-01T13:30:00Z', // 1h 30m out
        })}
      />,
    );
    expect(screen.getByTestId('task-card-lease').textContent).toBe('1h 30m');

    rerender(
      <TaskCard
        nowMs={NOW}
        task={makeTask({
          state: 'in_progress',
          worker_agent_id: 'coder-1',
          lease_expires_at: '2026-10-01T11:00:00Z', // already past
        })}
      />,
    );
    expect(screen.getByTestId('task-card-lease').textContent).toBe('expired');
  });
});
