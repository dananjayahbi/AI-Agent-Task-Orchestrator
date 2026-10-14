'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FormBanner } from '@/components/projects/form-field';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { callApi, isApiError, partialUpdateProject } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import { queryKeys } from '@/lib/queries/keys';
import { usePolicyQuery } from '@/lib/queries/policy';
import { useProjectQuery } from '@/lib/queries/projects';
import {
  DEFAULT_LEASE_MINUTES,
  PROJECT_RULES_MAX_CHARS,
  renderRulesPreview,
  type RulesRole,
} from '@/lib/projects/agent-rules';

/**
 * Rules editor (MT-4.2-02; FR-WEB-09) — `system_prompt_rules`, the markdown
 * the bridge injects into every agent's rules block (Section 10.6). The
 * value round-trips verbatim: no trimming, no reformatting, exact bytes go
 * back in the PATCH (WP-2.7 consumer expectation — risk note).
 *
 * MT-4.10-04 adds the rules-block preview (Section 13.1/19): what an agent
 * will receive — the Section 10.6 standard rules from the WP-2.7 templates
 * (`lib/projects/agent-rules.ts`, drift-pinned) with the draft appended —
 * plus the auditor-variant toggle, the Section 12.2 fieldset read-only gate
 * and the "applies on next connect/claim" effect-timing note (Section 10.6 —
 * running sessions keep their startup context; no false instant-rewrite
 * claim).
 */
export function RulesForm({ pid }: { pid: string }) {
  const queryClient = useQueryClient();
  const project = useProjectQuery(pid);
  const policy = usePolicyQuery(pid);
  const [text, setText] = useState<string | null>(null);
  const [baseline, setBaseline] = useState('');
  const [feedback, setFeedback] = useState<{ kind: 'error' | 'success'; text: string } | null>(
    null,
  );
  const [role, setRole] = useState<RulesRole>('coder');
  const [readOnly, setReadOnly] = useState(false);

  // Load/reload current server value via render-phase adjustment (server
  // truth wins; unchanged refetches keep identity and never clobber edits).
  const serverRules = project.data?.system_prompt_rules;
  const [syncedRules, setSyncedRules] = useState<string | undefined>(undefined);
  if (serverRules !== undefined && serverRules !== syncedRules) {
    setSyncedRules(serverRules);
    setText(serverRules);
    setBaseline(serverRules);
  }

  const save = useMutation({
    mutationFn: (rules: string) =>
      callApi(partialUpdateProject({ path: { pid }, body: { system_prompt_rules: rules } })),
    onSuccess: () => {
      setFeedback({ kind: 'success', text: 'Rules saved.' });
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(pid) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
    onError: (error) => {
      const friendly = resolveError(error);
      setFeedback({ kind: 'error', text: friendly.message });
      // Section 12.2 — an Owner-only PATCH rejected for a lesser role
      // (raised contract gap: no client maps 403 yet; same as MT-4.10-03).
      if (isApiError(error) && error.code === 'ROLE_NOT_PERMITTED') {
        setReadOnly(true);
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(pid) });
    },
  });

  if (text === null) {
    return null; // parent renders the shared loading/error state
  }

  // Preview cadence: the policy's lease (Section 7.2 default when the policy
  // query is still loading or failed — the bridge falls back the same way).
  const leaseMinutes = policy.data?.lease_duration_minutes ?? DEFAULT_LEASE_MINUTES;

  return (
    <form
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        save.mutate(text);
      }}
      noValidate
      className="grid max-w-lg gap-4"
    >
      {feedback !== null && <FormBanner variant={feedback.kind}>{feedback.text}</FormBanner>}
      {readOnly && (
        <div
          role="status"
          data-testid="rules-read-only-notice"
          className="rounded-md border border-border bg-muted/50 p-3 text-sm"
        >
          You can view this form, but your role doesn&apos;t allow editing project settings.
        </div>
      )}
      {/* Section 12.2 fieldset gate — one disabled switch carries the
          read-only/pending state to every control inside. */}
      <fieldset disabled={readOnly || save.isPending} className="grid gap-4">
        <Textarea
          id="rules-editor"
          aria-label="Agent rules (markdown)"
          rows={10}
          value={text}
          onChange={(event) => {
            setFeedback(null);
            setText(event.target.value);
          }}
        />
        <p className="text-xs text-muted-foreground" data-testid="rules-char-count">
          {text.length} / {PROJECT_RULES_MAX_CHARS} characters — the bridge caps appended project
          rules at the documented limit; the server validates the saved value.
        </p>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={save.isPending || text === baseline}>
            {save.isPending ? 'Saving…' : 'Save rules'}
          </Button>
          {text !== baseline && (
            <span className="text-xs text-muted-foreground">Unsaved changes</span>
          )}
        </div>
        {/* Section 10.6 preview: standard template first, draft appended —
            inert plain text (Principle P10), never executed or HTML-rendered. */}
        <div className="grid gap-2" data-testid="rules-preview-panel">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-semibold">Rules block preview</span>
            <div role="group" aria-label="Preview role" className="flex gap-1">
              {(['coder', 'auditor'] as const).map((option) => (
                <Button
                  key={option}
                  type="button"
                  variant={role === option ? 'default' : 'outline'}
                  size="sm"
                  aria-pressed={role === option}
                  data-testid={`rules-preview-toggle-${option}`}
                  onClick={() => setRole(option)}
                >
                  {option === 'coder' ? 'Coder' : 'Auditor'}
                </Button>
              ))}
            </div>
          </div>
          <pre
            data-testid="rules-preview"
            className="whitespace-pre-wrap rounded-md border bg-muted/40 p-3 text-xs"
          >
            {renderRulesPreview(role, text, leaseMinutes)}
          </pre>
          <p className="text-xs text-muted-foreground">
            Illustrative only — the block is delivered on the agent&apos;s next connect or claim
            (Section 10.6); sessions already running keep the project context they loaded at
            startup. Project rules are shown exactly as the bridge normalises them (control
            characters stripped, capped at {PROJECT_RULES_MAX_CHARS} characters).
          </p>
        </div>
      </fieldset>
    </form>
  );
}
