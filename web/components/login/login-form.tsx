'use client';

import { useState, type FormEvent } from 'react';

import { useRouter } from 'next/navigation';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { loginRequest } from '@/lib/api/auth';
import { isApiError } from '@/lib/api/client';
import { resolveError } from '@/lib/errors';
import { saveSessionUser } from '@/lib/session/store';

type LoginFormProps = {
  returnTo: string;
};

/**
 * Login form (MT-4.1-02): credentials go to the backend session endpoint
 * through the API seam; the HTTP-only session cookie is set by the response —
 * this component persists only the non-secret identity (Section 12.2) and
 * resumes at the sanitized return path.
 */
export function LoginForm({ returnTo }: LoginFormProps) {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const user = await loginRequest({ username, password });
      saveSessionUser(user);
      router.replace(returnTo);
      router.refresh();
    } catch (error) {
      // Inline copy comes from the shared catalog keyed by the canonical
      // code — never the raw server message (Section 13.3; G-07).
      const friendly = resolveError(isApiError(error) ? { code: error.code } : null);
      setErrorMessage(friendly.message);
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>
          Sign in to the AI Agent Task Orchestrator operations board.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4" noValidate>
          {errorMessage !== null && (
            <Alert variant="destructive">
              <AlertTitle>Sign-in failed</AlertTitle>
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              name="username"
              autoComplete="username"
              required
              autoFocus
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
