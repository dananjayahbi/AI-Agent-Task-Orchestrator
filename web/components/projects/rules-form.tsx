'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FormBanner } from '@/components/projects/form-field';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { callApi, partialUpdateProject } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import { queryKeys } from '@/lib/queries/keys';
import { useProjectQuery } from '@/lib/queries/projects';

/**
 * Rules editor (MT-4.2-02; FR-WEB-09) — `system_prompt_rules`, the markdown
 * the bridge injects into every agent's rules block (Section 10.6). The
 * value round-trips verbatim: no trimming, no reformatting, exact bytes go
 * back in the PATCH (WP-2.7 consumer expectation — risk note).
 */
export function RulesForm({ pid }: { pid: string }) {
  const queryClient = useQueryClient();
  const project = useProjectQuery(pid);
  const [text, setText] = useState<string | null>(null);
  const [baseline, setBaseline] = useState('');
  const [feedback, setFeedback] = useState<{ kind: 'error' | 'success'; text: string } | null>(
    null,
  );

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
      void queryClient.invalidateQueries({ queryKey: queryKeys.project(pid) });
    },
  });

  if (text === null) {
    return null; // parent renders the shared loading/error state
  }

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
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={save.isPending || text === baseline}>
          {save.isPending ? 'Saving…' : 'Save rules'}
        </Button>
        {text !== baseline && (
          <span className="text-xs text-muted-foreground">Unsaved changes</span>
        )}
      </div>
    </form>
  );
}
