"""Business services for the projects app (Section 9.1).

Views stay thin: PID allocation, pair-creating writes and manifest rendering
live here, independently testable and reusable by later work packages (the
task registry of WP-1.4 locks rows through the same primitives the CRUD of
MT-1.3-03 calls).

The package init deliberately re-exports nothing: consumers import the
specific submodule (``services.pids``, ``services.projects``,
``services.manifest``) so the accounts model layer can depend on the id
module without dragging manifest/policy code into app loading.
"""

from __future__ import annotations
