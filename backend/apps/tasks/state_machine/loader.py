"""Register the WP-1.5 rows into the default registry, once (MT-1.5-01).

Each table module exposes ``register(registry)``; the loader calls all
three the first time any dispatch resolves a pair. Registration is
import-side-effect free (functions, not module-level calls) so tests can
snapshot and restore ``DEFAULT_REGISTRY`` deterministically, and a later
WP's ``replace=True`` rewire is never clobbered by a second import —
``_registered`` makes the fill idempotent for the process lifetime.
"""

from __future__ import annotations

_registered = False


def ensure_registered() -> None:
    """Fill ``DEFAULT_REGISTRY`` with T2–T19 (idempotent)."""
    global _registered
    if _registered:
        return
    from . import transitions_agent, transitions_owner, transitions_system

    # Import order mirrors the micro-task order (owner, system, agent);
    # triggers are unique so order carries no meaning.
    for module in (transitions_owner, transitions_system, transitions_agent):
        module.register()
    _registered = True
