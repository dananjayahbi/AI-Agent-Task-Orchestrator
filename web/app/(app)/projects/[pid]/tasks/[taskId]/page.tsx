import { PagePlaceholder } from '@/components/layout/page-placeholder';

/**
 * Task detail (Section 13.1 — drawer or page: description, criteria, scope,
 * attachments, checkpoint feed, resolutions, audit reports, history; WP-4.6).
 */
export default async function TaskDetailPage({
  params,
}: {
  params: Promise<{ pid: string; taskId: string }>;
}) {
  const { pid, taskId } = await params;
  return (
    <PagePlaceholder
      title={`Task ${taskId} — ${pid}`}
      description="Description, acceptance criteria, scope, attachments, checkpoint feed, resolutions, audit reports, and transition history."
    />
  );
}
