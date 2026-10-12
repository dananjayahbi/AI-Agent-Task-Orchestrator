#!/usr/bin/env python
"""Django's command-line utility (parent plan Section 6.6; run via `uv`)."""

from __future__ import annotations

import os
import sys


def main() -> None:
    """Run administrative tasks against the dev settings module by default.

    Host runs (local machines, CI) default to dev settings; the container image
    overrides DJANGO_SETTINGS_MODULE to the prod module at the image boundary
    (see backend/Dockerfile), so exactly one selector is ever in play.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.core.settings.dev")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
