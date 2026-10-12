"""Agent credential loading surface (parent plan Section 10.3 step 3; FR-SEC-04).

Placeholder module — MT-2.1-01 seeds the seam only. The agent token itself is held
by the configuration loader (MT-2.1-02): environment variable or user-level config
file only, never the manifest and never a repo-tracked file. Session-time token
use and the missing-token message land with WP-2.2 (MT-2.2-03).
"""
