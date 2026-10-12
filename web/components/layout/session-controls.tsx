'use client';

import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { useSession } from '@/components/session/session-context';

/**
 * Account controls in the app chrome (MT-4.1-02): shows the non-secret
 * identity and runs the idempotent logout flow (backend revoke → local clear
 * → login redirect).
 */
export function SessionControls() {
  const { user, signOut } = useSession();
  const [busy, setBusy] = useState(false);

  async function handleSignOut() {
    setBusy(true);
    try {
      await signOut();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground" data-testid="session-username">
        {user !== null ? user.username : 'Signed in'}
      </span>
      <Button variant="outline" size="sm" onClick={handleSignOut} disabled={busy}>
        {busy ? 'Signing out…' : 'Sign out'}
      </Button>
    </div>
  );
}
