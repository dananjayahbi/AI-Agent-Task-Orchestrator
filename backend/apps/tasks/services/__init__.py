"""Business services for the tasks app (Section 9.1).

Views stay thin: id allocation, task writes (create/update/archive) and the
dependency rules live here, independently testable and reusable by later
work packages (WP-1.5's transition service calls the same primitives the
CRUD of MT-1.4-03 calls).

The package init deliberately re-exports nothing: consumers import the
specific submodule (``services.ids``, ``services.tasks``,
``services.dependencies``) so the model layer can depend on the id module
without dragging write/dependency code into app loading.
"""

from __future__ import annotations
