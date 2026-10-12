"""Resume-context cache seam (parent plan Sections 10.1, 10.3 step 5, 10.10).

Placeholder module — MT-2.1-01 seeds the seam only. After the session binds, the
bridge caches project context (name, policy summary, rules) per Section 10.3 step 5
so a reconnect or restart resumes without re-fetching; implementation lands with
WP-2.2 (MT-2.2-04 session lifecycle with project-context caching).
"""
