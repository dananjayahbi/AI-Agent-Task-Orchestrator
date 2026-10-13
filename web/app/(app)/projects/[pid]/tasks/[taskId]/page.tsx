import { TaskDetail } from '@/components/task/detail/task-detail';

/**
 * Task detail route (Section 13.1 "Task detail (drawer or page)";
 * WP-4.6 — MT-4.6-01 chose the **page** form: the route already exists,
 * deep links stay stable for WP-4.8, and the app-layout query cache
 * survives board ↔ detail navigation (Section 13.3). Recorded in the WP
 * changelog).
 */
export default async function TaskDetailPage({
  params,
}: {
  params: Promise<{ pid: string; taskId: string }>;
}) {
  const { pid, taskId } = await params;
  return <TaskDetail pid={pid} taskId={taskId} />;
}
