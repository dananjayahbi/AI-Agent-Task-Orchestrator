"""``python -m orchestrator_bridge`` — the generic module entry (Section 10.11; MT-2.1-04).

Same shared path as the ``orchestrator-bridge`` console script: ``--mode``
selects a run mode explicitly, otherwise config/default precedence applies.
"""

from __future__ import annotations

import sys

from .entrypoints import cli_entry


def main() -> int:
    """Module entry: parse argv, dispatch the selected run mode."""
    return cli_entry()


if __name__ == "__main__":
    sys.exit(main())
