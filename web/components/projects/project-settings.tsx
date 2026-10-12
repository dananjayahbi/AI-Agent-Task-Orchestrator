'use client';

import { EditProjectForm } from '@/components/projects/edit-project-form';
import { FormBanner } from '@/components/projects/form-field';
import { ManifestSection } from '@/components/projects/manifest-section';
import { PolicyForm } from '@/components/projects/policy-form';
import { ProjectStatusActions } from '@/components/projects/project-status-actions';
import { RulesForm } from '@/components/projects/rules-form';
import { StatusBadge } from '@/components/projects/status-badge';
import { TokenSection } from '@/components/projects/token-section';
import { ErrorState } from '@/components/errors/error-state';
import { LoadingState } from '@/components/states/loading-state';
import { resolveError } from '@/lib/errors';
import { useProjectQuery } from '@/lib/queries/projects';

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4">
      <h2 className="text-base font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}

/**
 * Project settings shell (Section 13.1: policy editor, rules editor,
 * manifest download, agent token management) — composed by MT-4.2-02
 * (details/policy/rules), MT-4.2-03 (manifest) and MT-4.2-04 (tokens).
 */
export function ProjectSettings({ pid, createdPid }: { pid: string; createdPid?: string }) {
  const project = useProjectQuery(pid);

  if (project.isPending) {
    return <LoadingState label="Loading project…" />;
  }
  if (project.isError) {
    const friendly = resolveError(project.error);
    return (
      <ErrorState
        title={friendly.title}
        message={friendly.message}
        requestId={friendly.requestId}
        onRetry={() => void project.refetch()}
      />
    );
  }

  const data = project.data;

  return (
    <div className="grid gap-8">
      {createdPid !== undefined && (
        <FormBanner variant="success">
          Project {createdPid} created — download its <code>orchestrator.json</code> manifest below
          to connect a repository.
        </FormBanner>
      )}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{data.name}</h1>
          <div className="mt-1 flex items-center gap-3">
            <span className="font-mono text-sm text-muted-foreground">{data.id}</span>
            <StatusBadge status={data.active_status} />
          </div>
        </div>
        <ProjectStatusActions project={data} />
      </div>

      <Section title="Details">
        <EditProjectForm pid={pid} project={data} />
      </Section>

      <Section title="Policy">
        <PolicyForm pid={pid} />
      </Section>

      <Section title="Agent rules">
        <RulesForm pid={pid} />
      </Section>

      <Section title="Manifest">
        <ManifestSection pid={pid} />
      </Section>

      <Section title="Agent tokens">
        <TokenSection pid={pid} />
      </Section>
    </div>
  );
}
