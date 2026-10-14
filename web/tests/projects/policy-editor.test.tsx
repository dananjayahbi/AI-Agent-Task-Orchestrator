/**
 * MT-4.10-03 — policy editor presets, validation and authorization
 * states (Sections 13.1, 7.2, 9.2, 12.2, 12.3).
 *
 * The field set itself (all Section 7.2 values, changed-fields PATCH)
 * is pinned by the MT-4.2-02 suite in `project-forms.test.tsx`; this
 * suite pins what WP-4.10 adds: preset population behind mandatory
 * confirmation (without losing other unsaved edits), the Section 12.3
 * glob mirror blocking invalid payloads, the defensive VERSION_CONFLICT
 * mapping, and the non-Owner read-only degrade.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { PolicyForm } from '@/components/projects/policy-form';
import { POLICY_PRESETS } from '@/lib/projects/policy-presets';
import {
  errorResponse,
  installApi,
  jsonResponse,
  makePolicy,
  renderWithQueryClient,
} from '../helpers/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

type RecordedPatch = Record<string, unknown>;

function setupPolicyForm(patchResponse: () => Response = () => jsonResponse(makePolicy())): {
  patchCalls: RecordedPatch[];
  getCalls: () => number;
} {
  let getCalls = 0;
  const patchCalls: RecordedPatch[] = [];
  installApi([
    {
      method: 'GET',
      match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
      respond: () => {
        getCalls += 1;
        return jsonResponse(makePolicy());
      },
    },
    {
      method: 'PATCH',
      match: /\/api\/v1\/projects\/PID00001\/policy(\?|$)/,
      respond: async ({ request }) => {
        patchCalls.push((await request.clone().json()) as RecordedPatch);
        return patchResponse();
      },
    },
  ]);
  renderWithQueryClient(<PolicyForm pid="PID00001" />);
  return { patchCalls, getCalls: () => getCalls };
}

describe('PolicyForm presets and states (MT-4.10-03)', () => {
  it('offers the WP-3.1 presets and populates the three glob lists only after confirmation, keeping other unsaved edits', async () => {
    setupPolicyForm();

    // Other unsaved edit first — the preset must not clobber it.
    const lease = (await screen.findByLabelText('Lease duration (minutes)')) as HTMLInputElement;
    fireEvent.change(lease, { target: { value: '50' } });

    const critical = screen.getByLabelText('critical path path globs') as HTMLTextAreaElement;
    expect(critical.value).toBe(makePolicy().critical_path_globs.join('\n'));

    const select = screen.getByTestId('policy-preset-select') as HTMLSelectElement;
    expect(Array.from(select.options).map((option) => option.value)).toEqual([
      'django',
      'nextjs',
      'flutter',
    ]);

    fireEvent.click(screen.getByTestId('policy-preset-apply'));
    const confirm = await screen.findByTestId('policy-preset-confirm');
    expect(within(confirm).getByText(/Existing glob values will be overwritten/)).toBeTruthy();
    // Not populated until the overwrite is confirmed.
    expect(critical.value).toBe(makePolicy().critical_path_globs.join('\n'));

    fireEvent.click(screen.getByTestId('policy-preset-confirm-apply'));
    expect(critical.value).toBe(POLICY_PRESETS.django.critical_path_globs.join('\n'));
    expect((screen.getByLabelText('migration path path globs') as HTMLTextAreaElement).value).toBe(
      POLICY_PRESETS.django.migration_path_globs.join('\n'),
    );
    expect(
      (screen.getByLabelText('sensitive config path globs') as HTMLTextAreaElement).value,
    ).toBe(POLICY_PRESETS.django.sensitive_config_globs.join('\n'));
    // The other unsaved edit survived.
    expect((screen.getByLabelText('Lease duration (minutes)') as HTMLInputElement).value).toBe(
      '50',
    );

    // Cancel path: a second preset attempt can still be abandoned.
    fireEvent.change(select, { target: { value: 'flutter' } });
    fireEvent.click(screen.getByTestId('policy-preset-apply'));
    fireEvent.click(await screen.findByTestId('policy-preset-confirm-cancel'));
    expect(screen.queryByTestId('policy-preset-confirm')).toBeNull();
    expect(critical.value).toBe(POLICY_PRESETS.django.critical_path_globs.join('\n'));
  });

  it('saves exactly the three changed glob lists when a confirmed preset is submitted', async () => {
    const { patchCalls } = setupPolicyForm();
    fireEvent.click(await screen.findByTestId('policy-preset-apply'));
    fireEvent.click(await screen.findByTestId('policy-preset-confirm-apply'));

    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));

    await waitFor(() => expect(patchCalls).toHaveLength(1));
    expect(Object.keys(patchCalls[0]).sort()).toEqual([
      'critical_path_globs',
      'migration_path_globs',
      'sensitive_config_globs',
    ]);
    expect(patchCalls[0].critical_path_globs).toEqual(POLICY_PRESETS.django.critical_path_globs);
  });

  it('mirrors Section 12.3 glob syntax client-side and never sends an invalid payload', async () => {
    const { patchCalls } = setupPolicyForm();
    const critical = (await screen.findByLabelText(
      'critical path path globs',
    )) as HTMLTextAreaElement;
    fireEvent.change(critical, { target: { value: '/absolute/path\n../escape' } });

    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));

    expect(await screen.findByText(/Invalid glob "\/absolute\/path"/)).toBeTruthy();
    expect(patchCalls).toHaveLength(0);
  });

  it('maps a defensive VERSION_CONFLICT to catalog copy and re-reads server truth', async () => {
    const { patchCalls, getCalls } = setupPolicyForm(() => errorResponse('VERSION_CONFLICT', 409));
    const retries = (await screen.findByLabelText('Max retries')) as HTMLInputElement;
    fireEvent.change(retries, { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));

    await waitFor(() => expect(patchCalls).toHaveLength(1));
    const banner = await screen.findByRole('alert');
    expect(banner.textContent).toContain('Someone else updated this first');
    // Rollback: the policy is re-read from the server.
    await waitFor(() => expect(getCalls()).toBeGreaterThanOrEqual(2));
  });

  it('degrades to a read-only form when the server rejects with ROLE_NOT_PERMITTED (Section 12.2)', async () => {
    setupPolicyForm(() => errorResponse('ROLE_NOT_PERMITTED', 403));
    const retries = (await screen.findByLabelText('Max retries')) as HTMLInputElement;
    fireEvent.change(retries, { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save policy' }));

    const banner = await screen.findByRole('alert');
    expect(banner.textContent).toContain("Your role doesn't allow this action");
    const notice = await screen.findByTestId('policy-read-only-notice');
    expect(notice.textContent).toContain('read-only');
    // The native fieldset gate (Section 12.2) carries the disabled state
    // to every control; jsdom reflects it on the fieldset itself.
    await waitFor(() => {
      const fieldset = document.querySelector('fieldset');
      expect(fieldset?.disabled).toBe(true);
    });
    // The save affordance stays visible but inert.
    expect(screen.getByRole('button', { name: 'Save policy' })).toBeTruthy();
  });
});
