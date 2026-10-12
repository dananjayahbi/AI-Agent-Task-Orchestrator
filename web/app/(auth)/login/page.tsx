import { LoginForm } from '@/components/login/login-form';
import { sanitizeReturnPath } from '@/lib/auth/return-path';

/**
 * Login (Section 13.1 — the only public route). Unauthenticated visitors are
 * sent here by proxy.ts with `?next=<return path>`; authenticated visitors
 * bounce off this page back to the Board (MT-4.1-02).
 */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string | string[] }>;
}) {
  const params = await searchParams;
  const returnTo = sanitizeReturnPath(typeof params.next === 'string' ? params.next : undefined);
  return <LoginForm returnTo={returnTo} />;
}
