'use client';

import { useState } from 'react';

import { ErrorState } from '@/components/errors/error-state';
import { FormBanner } from '@/components/projects/form-field';
import { LoadingState } from '@/components/states/loading-state';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { resolveError } from '@/lib/errors';
import { useManifestQuery } from '@/lib/queries/manifest';

const FILE_NAME = 'orchestrator.json';

/**
 * Manifest download + copy (MT-4.2-03; FR-PRJ-03; Section 10.3). The bytes
 * come straight from `GET /projects/{pid}/manifest` (fetched as raw text) —
 * nothing is assembled client-side, so the file always matches the server
 * document the bridge validates. The manifest carries no secrets and is safe
 * to commit; agent tokens are deliberately a separate flow (MT-4.2-04).
 */
export function ManifestSection({ pid }: { pid: string }) {
  const manifest = useManifestQuery(pid);
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

  if (manifest.isPending) {
    return <LoadingState label="Loading manifest…" />;
  }
  if (manifest.isError) {
    const friendly = resolveError(manifest.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void manifest.refetch()}
      />
    );
  }

  const text = manifest.data;

  function download() {
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = FILE_NAME;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopyState('copied');
    } catch {
      // Clipboard APIs fail on non-secure origins — fall back to selectable
      // text rather than a dead button (MT-4.2-03 risk note).
      setCopyState('failed');
    }
  }

  return (
    <div className="grid max-w-lg gap-4">
      <p className="text-sm text-muted-foreground">
        The manifest ties a repository to this project: place{' '}
        <code className="font-mono text-xs">orchestrator.json</code> at your repository root, then
        run the bridge&apos;s <code className="font-mono text-xs">init</code> command to bind it.
      </p>

      <div className="flex flex-wrap gap-2">
        <Button onClick={download}>Download orchestrator.json</Button>
        <Button variant="outline" onClick={() => void copy()}>
          Copy to clipboard
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        This manifest contains no secrets — it is safe to commit. Agent tokens are never part of it;
        they are created separately below.
      </p>

      {copyState === 'copied' && (
        <FormBanner variant="success">Manifest copied to clipboard.</FormBanner>
      )}
      {copyState === 'failed' && (
        <>
          <FormBanner variant="error">
            Copying was blocked by the browser — select the text below and copy it manually.
          </FormBanner>
          <Textarea
            aria-label="Manifest text"
            readOnly
            rows={8}
            value={text}
            onFocus={(event) => event.currentTarget.select()}
          />
        </>
      )}
    </div>
  );
}
