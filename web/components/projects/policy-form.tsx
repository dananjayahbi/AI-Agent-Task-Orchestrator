'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FieldRow, FormBanner } from '@/components/projects/form-field';
import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { callApi, partialUpdateProjectPolicy, type ProjectPolicy } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import {
  validatePolicyFields,
  type FieldErrors,
  type PolicyFormValues,
} from '@/lib/forms/project-schemas';
import { queryKeys } from '@/lib/queries/keys';
import { usePolicyQuery } from '@/lib/queries/policy';
import { cn } from 'cn';

/** Option lists typed against the generated unions (contract = source). */
const LEASE_MODES: ProjectPolicy['lease_extension_mode'][] = [
  'checkpoint_only',
  'checkpoint_and_liveness',
];
const MERGE_STRATEGIES: ProjectPolicy['merge_strategy'][] = [
  'squash',
  'merge_commit',
  'fast_forward_only',
];

const GLOB_FIELDS = [
  'critical_path_globs',
  'migration_path_globs',
  'sensitive_config_globs',
] as const;
type GlobField = (typeof GLOB_FIELDS)[number];

type FormState = PolicyFormValues &
  Record<GlobField, string> & {
    auto_complete_enabled: boolean;
    audit_required_default: boolean;
    merge_strategy: ProjectPolicy['merge_strategy'];
  };

type Baseline = { policy: ProjectPolicy; state: FormState };

function toState(policy: ProjectPolicy): FormState {
  return {
    lease_duration_minutes: String(policy.lease_duration_minutes),
    lease_max_total_minutes: String(policy.lease_max_total_minutes),
    lease_extension_mode: policy.lease_extension_mode,
    max_retries: String(policy.max_retries),
    max_concurrent_tasks: String(policy.max_concurrent_tasks),
    autonomous_diff_threshold_lines: String(policy.autonomous_diff_threshold_lines),
    auditor_min_confidence: String(policy.auditor_min_confidence),
    stalled_after_minutes: String(policy.stalled_after_minutes),
    branch_prefix: policy.branch_prefix,
    critical_path_globs: policy.critical_path_globs.join('\n'),
    migration_path_globs: policy.migration_path_globs.join('\n'),
    sensitive_config_globs: policy.sensitive_config_globs.join('\n'),
    auto_complete_enabled: policy.auto_complete_enabled,
    audit_required_default: policy.audit_required_default,
    merge_strategy: policy.merge_strategy,
  };
}

function parseGlobs(raw: string): string[] {
  // Split on newlines; blank lines are user noise, real entries keep their
  // exact text (round-trip preserves server values byte-for-byte).
  return raw.split('\n').filter((line) => line.trim() !== '');
}

/**
 * Policy editor (MT-4.2-02; FR-WEB-09). Values are loaded from
 * `GET /projects/{pid}/policy` — never client-invented defaults (risk note:
 * a wrong default could silently weaken review requirements). Save sends
 * only changed fields via `PATCH /projects/{pid}/policy`.
 */
export function PolicyForm({ pid }: { pid: string }) {
  const queryClient = useQueryClient();
  const policy = usePolicyQuery(pid);
  const [state, setState] = useState<FormState | null>(null);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [feedback, setFeedback] = useState<{ kind: 'error' | 'success'; text: string } | null>(
    null,
  );

  // Load current server values (and re-baseline after save/conflict) via
  // render-phase adjustment — unchanged refetches keep identity, so user
  // edits are never clobbered by an equal server response.
  const [syncedPolicy, setSyncedPolicy] = useState<ProjectPolicy | undefined>(undefined);
  if (policy.data !== undefined && policy.data !== syncedPolicy) {
    setSyncedPolicy(policy.data);
    const next = toState(policy.data);
    setState(next);
    setBaseline({ policy: policy.data, state: next });
    setErrors({});
  }

  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      callApi(partialUpdateProjectPolicy({ path: { pid }, body })),
    onSuccess: () => {
      setFeedback({ kind: 'success', text: 'Policy saved. It applies from the next claim.' });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectPolicy(pid) });
    },
    onError: (error) => {
      const friendly = resolveError(error);
      setFeedback({ kind: 'error', text: friendly.message });
      // Roll back to the latest server values.
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectPolicy(pid) });
    },
  });

  if (policy.isPending || state === null || baseline === null) {
    if (policy.isError) {
      const friendly = resolveError(policy.error);
      return (
        <ErrorState
          title={friendly.title}
          message={friendly.message}
          requestId={friendly.requestId}
          onRetry={() => void policy.refetch()}
        />
      );
    }
    return <LoadingState label="Loading policy…" />;
  }

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setFeedback(null);
    setState((current) => (current === null ? current : { ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state === null || baseline === null) return;
    const fieldErrors = validatePolicyFields(state);
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;

    const before = baseline.state;
    const body: Record<string, unknown> = {};
    const numeric: Array<keyof PolicyFormValues> = [
      'lease_duration_minutes',
      'lease_max_total_minutes',
      'max_retries',
      'max_concurrent_tasks',
      'autonomous_diff_threshold_lines',
      'auditor_min_confidence',
      'stalled_after_minutes',
    ];
    for (const field of numeric) {
      if (state[field] !== before[field]) body[field] = Number(state[field]);
    }
    for (const field of ['lease_extension_mode', 'branch_prefix'] as const) {
      if (state[field] !== before[field]) body[field] = state[field];
    }
    for (const field of GLOB_FIELDS) {
      if (state[field] !== before[field]) body[field] = parseGlobs(state[field]);
    }
    for (const field of [
      'auto_complete_enabled',
      'audit_required_default',
      'merge_strategy',
    ] as const) {
      if (state[field] !== before[field]) body[field] = state[field];
    }

    if (Object.keys(body).length === 0) {
      setFeedback({ kind: 'success', text: 'Nothing to save — no changes.' });
      return;
    }
    save.mutate(body);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="grid max-w-lg gap-4">
      {feedback !== null && <FormBanner variant={feedback.kind}>{feedback.text}</FormBanner>}

      <div className="grid gap-4 sm:grid-cols-2">
        <FieldRow
          htmlFor="lease-duration"
          label="Lease duration (minutes)"
          error={errors.lease_duration_minutes}
        >
          <Input
            id="lease-duration"
            inputMode="numeric"
            value={state.lease_duration_minutes}
            aria-invalid={errors.lease_duration_minutes !== undefined}
            onChange={(event) => set('lease_duration_minutes', event.target.value)}
          />
        </FieldRow>
        <FieldRow
          htmlFor="lease-max-total"
          label="Max continuous claim (minutes)"
          error={errors.lease_max_total_minutes}
        >
          <Input
            id="lease-max-total"
            inputMode="numeric"
            value={state.lease_max_total_minutes}
            aria-invalid={errors.lease_max_total_minutes !== undefined}
            onChange={(event) => set('lease_max_total_minutes', event.target.value)}
          />
        </FieldRow>
        <FieldRow htmlFor="max-retries" label="Max retries" error={errors.max_retries}>
          <Input
            id="max-retries"
            inputMode="numeric"
            value={state.max_retries}
            aria-invalid={errors.max_retries !== undefined}
            onChange={(event) => set('max_retries', event.target.value)}
          />
        </FieldRow>
        <FieldRow
          htmlFor="max-concurrent"
          label="Max concurrent tasks"
          error={errors.max_concurrent_tasks}
        >
          <Input
            id="max-concurrent"
            inputMode="numeric"
            value={state.max_concurrent_tasks}
            aria-invalid={errors.max_concurrent_tasks !== undefined}
            onChange={(event) => set('max_concurrent_tasks', event.target.value)}
          />
        </FieldRow>
        <FieldRow
          htmlFor="diff-threshold"
          label="Autocomplete diff threshold (lines)"
          error={errors.autonomous_diff_threshold_lines}
        >
          <Input
            id="diff-threshold"
            inputMode="numeric"
            value={state.autonomous_diff_threshold_lines}
            aria-invalid={errors.autonomous_diff_threshold_lines !== undefined}
            onChange={(event) => set('autonomous_diff_threshold_lines', event.target.value)}
          />
        </FieldRow>
        <FieldRow
          htmlFor="auditor-confidence"
          label="Auditor min confidence (1–5)"
          error={errors.auditor_min_confidence}
        >
          <Input
            id="auditor-confidence"
            inputMode="numeric"
            value={state.auditor_min_confidence}
            aria-invalid={errors.auditor_min_confidence !== undefined}
            onChange={(event) => set('auditor_min_confidence', event.target.value)}
          />
        </FieldRow>
        <FieldRow
          htmlFor="stalled-after"
          label="Stalled warning after (minutes)"
          error={errors.stalled_after_minutes}
        >
          <Input
            id="stalled-after"
            inputMode="numeric"
            value={state.stalled_after_minutes}
            aria-invalid={errors.stalled_after_minutes !== undefined}
            onChange={(event) => set('stalled_after_minutes', event.target.value)}
          />
        </FieldRow>
        <FieldRow htmlFor="branch-prefix" label="Branch prefix" error={errors.branch_prefix}>
          <Input
            id="branch-prefix"
            value={state.branch_prefix}
            aria-invalid={errors.branch_prefix !== undefined}
            onChange={(event) => set('branch_prefix', event.target.value)}
          />
        </FieldRow>
        <FieldRow htmlFor="lease-extension" label="Lease extension mode">
          <select
            id="lease-extension"
            value={state.lease_extension_mode}
            onChange={(event) =>
              set('lease_extension_mode', event.target.value as FormState['lease_extension_mode'])
            }
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-base md:text-sm dark:bg-input/30"
          >
            {LEASE_MODES.map((mode) => (
              <option key={mode} value={mode}>
                {mode.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </FieldRow>
        <FieldRow htmlFor="merge-strategy" label="Merge strategy">
          <select
            id="merge-strategy"
            value={state.merge_strategy}
            onChange={(event) =>
              set('merge_strategy', event.target.value as ProjectPolicy['merge_strategy'])
            }
            className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-base md:text-sm dark:bg-input/30"
          >
            {MERGE_STRATEGIES.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </FieldRow>
      </div>

      {GLOB_FIELDS.map((field) => (
        <FieldRow
          key={field}
          htmlFor={`policy-${field}`}
          label={`${field.replace(/_/g, ' ').replace(' globs', '')} path globs`}
          hint="One glob per line."
        >
          <Textarea
            id={`policy-${field}`}
            rows={3}
            value={state[field]}
            onChange={(event) => set(field, event.target.value)}
          />
        </FieldRow>
      ))}

      <div className="flex flex-wrap gap-4">
        <label className={cn('flex items-center gap-2 text-sm')}>
          <input
            type="checkbox"
            checked={state.auto_complete_enabled}
            onChange={(event) => set('auto_complete_enabled', event.target.checked)}
          />
          Auto-complete small diffs
        </label>
        <label className={cn('flex items-center gap-2 text-sm')}>
          <input
            type="checkbox"
            checked={state.audit_required_default}
            onChange={(event) => set('audit_required_default', event.target.checked)}
          />
          Audit required by default
        </label>
      </div>

      <div>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? 'Saving…' : 'Save policy'}
        </Button>
      </div>
    </form>
  );
}
