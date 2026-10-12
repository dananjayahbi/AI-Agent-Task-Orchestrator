"""Environment-variable readers for the settings modules (Sections 9.10, 16.2).

Every value is read from its canonical ``ORCHESTRATOR_*`` name as fixed by
``docs/plan/conventions/configuration.md`` — one name, no aliases. Empty
values count as unset so a template placeholder like ``ORCHESTRATOR_DATABASE_URL=``
falls back to the documented default. Booleans accept only ``true`` / ``false``
(configuration.md rule 5) and fail fast on anything else.
"""

from __future__ import annotations

import os


def get_str(name: str, default: str) -> str:
    """Return the stripped environment value for *name*, or *default* when unset/empty."""
    value = os.environ.get(name, "").strip()
    return value if value else default


def get_bool(name: str, default: bool) -> bool:
    """Return the boolean environment value for *name* (``true``/``false``).

    An unset/empty value yields *default*; any other spelling raises so a
    misconfigured deployment fails at startup instead of silently guessing.
    """
    value = get_str(name, "")
    if not value:
        return default
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"{name} must be 'true' or 'false' (got {value!r})")


def get_int(name: str, default: int) -> int:
    """Return the positive-integer environment value for *name*, or *default*.

    Used by the Section 9.10 groups whose metadata contract requires a
    positive integer (token lifetimes, rate limits — configuration.md). An
    unset/empty value yields *default*; a non-integer or non-positive value
    raises so a misconfigured deployment fails at startup (Section 9.10).
    """
    value = get_str(name, "")
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer (got {value!r})") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be a positive integer (got {parsed})")
    return parsed


def get_list(name: str, default: list[str]) -> list[str]:
    """Return a comma-separated environment value as a list of non-empty items.

    Unset/empty yields *default*; a set value replaces it entirely (no merging),
    so the effective list is always exactly what the environment declares.
    """
    raw = get_str(name, "")
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]
