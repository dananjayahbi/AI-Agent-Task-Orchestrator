/**
 * Query key factory (MT-4.2-01; Section 13.3 server-state caching).
 * One place defines the cache identity so invalidation after mutations
 * (create/edit/revoke) always hits the right entries.
 */
export const queryKeys = {
  projects: ['projects'] as const,
  project: (pid: string) => ['projects', pid] as const,
  projectPolicy: (pid: string) => ['projects', pid, 'policy'] as const,
  projectManifest: (pid: string) => ['projects', pid, 'manifest'] as const,
  projectTokens: (pid: string) => ['projects', pid, 'tokens'] as const,
};
