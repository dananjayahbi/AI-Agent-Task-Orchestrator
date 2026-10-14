import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RulesForm } from '@/components/projects/rules-form';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makePolicy,
  makeProject,
  renderWithQueryClient,
  type Route,
} from '../helpers/api';

function rulesRoutes(rules: string, extra: Route[] = []): Route[] {
  return [
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001(\?|$)/,
      respond: () => jsonResponse(makeProject({ system_prompt_rules: rules })),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001\/policy$/,
      respond: () => jsonResponse(makePolicy()),
    },
    ...extra,
  ];
}

describe('RulesForm preview (MT-4.10-04; Section 10.6)', () => {
  it('shows the coder block with generic slots, the draft appended, and the effect timing', async () => {
    installApi(rulesRoutes('Owner rule A'));
    renderWithQueryClient(<RulesForm pid="PID00001" />);

    const preview = await screen.findByTestId('rules-preview');
    expect(preview.textContent).toContain('Coder rules (Section 10.6):');
    expect(preview.textContent).toContain('the branch returned by claim_task');
    // makePolicy lease is 45 → one-third cadence (RISK-02).
    expect(preview.textContent).toContain('at least every 15 minutes');
    expect(preview.textContent).toContain('Project rules:');
    expect(preview.textContent).toContain('Owner rule A');
    // Section 10.6 effect timing — no false instant-rewrite claim.
    expect(screen.getByTestId('rules-preview-panel').textContent).toContain(
      'next connect or claim',
    );
  });

  it('toggles to the auditor variant and back', async () => {
    installApi(rulesRoutes('Owner rule A'));
    renderWithQueryClient(<RulesForm pid="PID00001" />);
    const preview = await screen.findByTestId('rules-preview');

    fireEvent.click(screen.getByTestId('rules-preview-toggle-auditor'));
    await waitFor(() => {
      expect(preview.textContent).toContain('Auditor rules (Section 10.6):');
      expect(preview.textContent).toContain("Run the project's full test and lint matrix.");
      expect(preview.textContent).not.toContain('Coder rules (Section 10.6):');
    });
    expect(screen.getByTestId('rules-preview-toggle-auditor').getAttribute('aria-pressed')).toBe(
      'true',
    );

    fireEvent.click(screen.getByTestId('rules-preview-toggle-coder'));
    await waitFor(() => {
      expect(preview.textContent).toContain('Coder rules (Section 10.6):');
    });
  });

  it('previews the live draft without saving and shows the truncation marker when over the cap', async () => {
    installApi(rulesRoutes('Owner rule A'));
    renderWithQueryClient(<RulesForm pid="PID00001" />);
    const preview = await screen.findByTestId('rules-preview');
    const editor = await screen.findByLabelText('Agent rules (markdown)');

    fireEvent.change(editor, { target: { value: 'Owner rule A\nSecond line' } });
    await waitFor(() => {
      expect(preview.textContent).toContain('Second line');
    });
    expect(screen.getByTestId('rules-char-count').textContent).toContain('/ 8000 characters');

    fireEvent.change(editor, { target: { value: 'z'.repeat(8010) } });
    await waitFor(() => {
      expect(preview.textContent).toContain('[project rules truncated: limit reached]');
    });
  });

  it('renders the draft as inert text — no HTML interpretation of markdown', async () => {
    installApi(rulesRoutes('<img src=x onerror="alert(1)"> <script>alert(2)</script>'));
    renderWithQueryClient(<RulesForm pid="PID00001" />);
    const preview = await screen.findByTestId('rules-preview');

    expect(preview.tagName).toBe('PRE');
    expect(preview.querySelector('img')).toBeNull();
    expect(preview.querySelector('script')).toBeNull();
    expect(preview.textContent).toContain('<img src=x onerror="alert(1)">');
  });

  it('flips to the Section 12.2 read-only gate when the PATCH is rejected as ROLE_NOT_PERMITTED', async () => {
    installApi(
      rulesRoutes('base', [
        {
          method: 'PATCH',
          match: /\/api\/v1\/projects\/PID00001$/,
          respond: () => errorResponse('ROLE_NOT_PERMITTED', 403, 'owner only'),
        },
      ]),
    );
    renderWithQueryClient(<RulesForm pid="PID00001" />);

    const editor = await screen.findByLabelText('Agent rules (markdown)');
    await waitFor(() => expect((editor as HTMLTextAreaElement).value).toBe('base'));
    fireEvent.change(editor, { target: { value: 'base\nchanged' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save rules' }));

    const notice = await screen.findByTestId('rules-read-only-notice');
    expect(notice.textContent).toContain("doesn't allow editing project settings");
    await waitFor(() => {
      const fieldset = document.querySelector('fieldset');
      expect(fieldset?.disabled).toBe(true);
    });
  });
});
