import { PagePlaceholder } from '@/components/layout/page-placeholder';

/**
 * Project settings (Section 13.1: policy editor, rules editor, manifest
 * download, agent token management; WP-4.2 / WP-4.10).
 */
export default async function ProjectSettingsPage({
  params,
}: {
  params: Promise<{ pid: string }>;
}) {
  const { pid } = await params;
  return (
    <PagePlaceholder
      title={`Project settings — ${pid}`}
      description="Policy editor, rules editor, manifest download, and agent token management."
    />
  );
}
