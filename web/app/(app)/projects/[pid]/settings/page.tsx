import { ProjectSettings } from '@/components/projects/project-settings';

/**
 * Project settings route (Section 13.1: policy editor, rules editor,
 * manifest download, agent token management; MT-4.2-02 fills the editors).
 * `?created={pid}` carries the create-flow hand-off from `/projects/new`
 * (MT-4.2-02 → MT-4.2-03 manifest step).
 */
export default async function ProjectSettingsPage({
  params,
  searchParams,
}: {
  params: Promise<{ pid: string }>;
  searchParams: Promise<{ created?: string }>;
}) {
  const { pid } = await params;
  const { created } = await searchParams;
  return <ProjectSettings pid={pid} createdPid={created} />;
}
