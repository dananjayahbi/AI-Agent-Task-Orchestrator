'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { FormBanner } from '@/components/projects/form-field';
import { EmptyState } from '@/components/states/empty-state';
import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { apiV1TokensAgentCreate, apiV1TokensDestroy, callApi, type TokenSummary } from '@/lib/api';
import { resolveError } from '@/lib/errors';
import { queryKeys } from '@/lib/queries/keys';
import { useAgentTokensQuery } from '@/lib/queries/tokens';

function formatScopes(scopes: unknown): string {
  if (Array.isArray(scopes) && scopes.length > 0) {
    return scopes.map((scope) => String(scope)).join(', ');
  }
  return 'default roles';
}

function formatDate(value: string | null): string {
  if (value === null) return '—';
  return new Date(value).toLocaleDateString();
}

/**
 * Agent token management (MT-4.2-04; Section 12.2 — project-scoped,
 * revocable, Owner-created; Section 9.2 token endpoints).
 *
 * Security posture (Section 12.4; Section 20.4 item 3):
 * - the plaintext exists only in component state for the one-time reveal —
 *   never in the query cache, localStorage/sessionStorage, logs or URLs;
 * - `GET /tokens` renders explicitly listed non-secret metadata only, so an
 *   API divergence exposing more fields still shows nothing extra;
 * - the value is dropped when the component unmounts or the route changes
 *   (React state dies with it — nothing else ever holds it).
 */
export function TokenSection({ pid }: { pid: string }) {
  const queryClient = useQueryClient();
  const tokens = useAgentTokensQuery(pid);

  const [issued, setIssued] = useState<{ id: number; token: string } | null>(null);
  const [copyAck, setCopyAck] = useState<'copied' | 'failed' | null>(null);
  const [pendingRevoke, setPendingRevoke] = useState<TokenSummary | null>(null);
  const [feedback, setFeedback] = useState<{ kind: 'error' | 'success'; text: string } | null>(
    null,
  );

  // One-time reveal hygiene: whatever held the value is dropped when this
  // section unmounts (navigation away) — nothing persisted, nothing cached.
  useEffect(() => {
    return () => {
      setIssued(null);
      setCopyAck(null);
    };
  }, []);

  const create = useMutation({
    mutationFn: () => callApi(apiV1TokensAgentCreate({ body: { project_id: pid } })),
    onSuccess: (issuedToken) => {
      setIssued({ id: issuedToken.id, token: issuedToken.token });
      setCopyAck(null);
      setFeedback(null);
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectTokens(pid) });
    },
    onError: (error) => setFeedback({ kind: 'error', text: resolveError(error).message }),
  });

  const revoke = useMutation({
    mutationFn: (id: number) => callApi(apiV1TokensDestroy({ path: { id } })),
    onSuccess: () => {
      setPendingRevoke(null);
      setFeedback({ kind: 'success', text: 'Token revoked.' });
      void queryClient.invalidateQueries({ queryKey: queryKeys.projectTokens(pid) });
    },
    onError: (error) => setFeedback({ kind: 'error', text: resolveError(error).message }),
  });

  async function copyIssued() {
    if (issued === null) return;
    try {
      await navigator.clipboard.writeText(issued.token);
      setCopyAck('copied');
    } catch {
      setCopyAck('failed'); // the value stays visible and selectable below
    }
  }

  if (tokens.isPending) {
    return <LoadingState label="Loading agent tokens…" />;
  }
  if (tokens.isError) {
    const friendly = resolveError(tokens.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void tokens.refetch()}
      />
    );
  }

  return (
    <div className="grid max-w-lg gap-4">
      {feedback !== null && <FormBanner variant={feedback.kind}>{feedback.text}</FormBanner>}

      {issued !== null && (
        <div
          data-testid="token-reveal"
          className="grid gap-3 rounded-lg border border-border bg-card p-4"
        >
          <div>
            <h3 className="text-sm font-semibold text-card-foreground">
              Token issued — copy it now
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              This is the only time the token will be shown. The server stores only its hash and
              cannot show it again.
            </p>
          </div>
          <code
            data-testid="token-value"
            className="block overflow-x-auto rounded-md border border-border bg-muted p-2 font-mono text-xs break-all"
          >
            {issued.token}
          </code>
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm" onClick={() => void copyIssued()}>
              Copy token
            </Button>
            <Button size="sm" variant="outline" onClick={() => setIssued(null)}>
              I saved it — dismiss
            </Button>
          </div>
          {copyAck === 'copied' && (
            <p role="status" className="text-xs text-muted-foreground">
              Token copied to clipboard.
            </p>
          )}
          {copyAck === 'failed' && (
            <p role="alert" className="text-xs text-destructive">
              Copying was blocked — select the token above and copy it manually.
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Store it in the host&apos;s user-level agent configuration or environment variable
            (Section 10.3 step 3) — never in <code className="font-mono">orchestrator.json</code>,
            which never carries tokens.
          </p>
        </div>
      )}

      <div>
        <Button disabled={create.isPending} onClick={() => create.mutate()}>
          {create.isPending ? 'Creating…' : 'Create agent token'}
        </Button>
      </div>

      {tokens.data.length === 0 ? (
        <EmptyState
          title="No agent tokens yet"
          description="Issue a project-scoped token for the bridge to authenticate with."
        />
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {tokens.data.map((token) => (
            <li key={token.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0 text-sm">
                <p className="font-mono text-xs text-muted-foreground">
                  Token #{token.id} · {formatScopes(token.scopes)}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {token.revoked_at !== null
                    ? `Revoked ${formatDate(token.revoked_at)}`
                    : `Active · last used ${token.last_used_at === null ? 'never' : formatDate(token.last_used_at)} · expires ${token.expires_at === null ? 'never' : formatDate(token.expires_at)}`}
                </p>
              </div>
              {token.revoked_at === null && (
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => {
                    setFeedback(null);
                    setPendingRevoke(token);
                  }}
                >
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={pendingRevoke !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingRevoke(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke this token?</DialogTitle>
            <DialogDescription>
              Agents using this token lose access immediately. This cannot be undone — issue a new
              token to replace it.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingRevoke(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={revoke.isPending}
              onClick={() => {
                if (pendingRevoke !== null) revoke.mutate(pendingRevoke.id);
              }}
            >
              {revoke.isPending ? 'Revoking…' : 'Revoke token'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
