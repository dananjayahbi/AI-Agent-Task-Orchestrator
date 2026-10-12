import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ApiErrorView } from '@/components/errors/api-error-view';
import { ErrorState } from '@/components/errors/error-state';
import { ApiError } from '@/lib/api/client';

/**
 * Presentation tests (MT-4.1-04): canonical codes drive the friendly states
 * rendered through shared components — denials never leak internal detail and
 * unknown codes degrade to generic copy + reference id (G-07; Section 13.3).
 */
describe('ApiErrorView', () => {
  it('renders the friendly project-access-denied state for AUTH_FORBIDDEN_PROJECT', () => {
    const error = new ApiError(403, {
      code: 'AUTH_FORBIDDEN_PROJECT',
      message: 'user 7 lacks scope project:read on PID00007',
      retryable: false,
      details: { project_id: 'PID00007', user_id: 7 },
      correlation_id: 'corr-403',
    });

    render(<ApiErrorView error={error} />);

    expect(screen.getByText("You don't have access")).toBeTruthy();
    expect(
      screen.getByText(
        "You don't have access to this project. If you think you should, ask the project owner to grant you access.",
      ),
    ).toBeTruthy();
    expect(screen.getByText('Reference ID: corr-403')).toBeTruthy();
    // No internal detail leaks (G-07).
    expect(screen.queryByText(/lacks scope/)).toBeNull();
    expect(screen.queryByText(/PID00007/)).toBeNull();
    expect(screen.queryByText(/user 7/)).toBeNull();
  });

  it('degrades an unknown code to the generic state with the request id', () => {
    const error = new ApiError(500, {
      code: 'SOME_FUTURE_CODE',
      message: 'raw server text',
      retryable: true,
      details: null,
      correlation_id: 'corr-77',
    });

    render(<ApiErrorView error={error} />);

    expect(screen.getByText('Something went wrong')).toBeTruthy();
    expect(screen.getByText("We couldn't complete that request. Please try again.")).toBeTruthy();
    expect(screen.getByText('Reference ID: corr-77')).toBeTruthy();
    expect(screen.queryByText('raw server text')).toBeNull();
  });

  it('never renders a raw non-API error message', () => {
    render(<ApiErrorView error={new Error('TypeError: cannot read properties of undefined')} />);

    expect(screen.getByText('Something went wrong')).toBeTruthy();
    expect(screen.queryByText(/cannot read properties/)).toBeNull();
  });

  it('offers a retry action when provided', () => {
    let retried = 0;
    render(<ApiErrorView error={new Error('boom')} onRetry={() => (retried += 1)} />);

    screen.getByRole('button', { name: 'Try again' }).click();
    expect(retried).toBe(1);
  });
});

describe('ErrorState', () => {
  it('renders catalog copy, support reference and alert semantics', () => {
    render(
      <ErrorState title="Task not found" message="This task does not exist." requestId="corr-9" />,
    );

    const region = screen.getByRole('alert');
    expect(region.textContent).toContain('Task not found');
    expect(region.textContent).toContain('This task does not exist.');
    expect(region.textContent).toContain('Reference ID: corr-9');
  });
});
