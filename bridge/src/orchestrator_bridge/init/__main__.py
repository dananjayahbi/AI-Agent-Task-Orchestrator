"""``python -m orchestrator_bridge.init`` — the init module entry (MT-2.12-01).

Same dispatcher as the ``orchestrator`` console script declared in
``pyproject.toml``: subcommands and flags are parsed by
:mod:`orchestrator_bridge.init.cli`.
"""

from __future__ import annotations

import sys

from .cli import main


def entry() -> int:
    """Module entry: parse process argv and run the requested init duty."""
    return main()


if __name__ == "__main__":
    sys.exit(entry())
