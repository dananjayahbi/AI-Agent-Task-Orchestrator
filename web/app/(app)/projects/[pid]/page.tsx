import { redirect } from 'next/navigation';

/** Project index routes to the project's board (Section 13.1 navigation). */
export default async function ProjectIndexPage({ params }: { params: Promise<{ pid: string }> }) {
  const { pid } = await params;
  redirect(`/projects/${pid}/board`);
}
