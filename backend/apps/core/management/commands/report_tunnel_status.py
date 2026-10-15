"""``report_tunnel_status`` — the documented tunnel-status reporter (MT-6.4-02).

The tunnel is outbound-only by design (Section 15.1), so the backend cannot
probe it; MT-6.4-02's tunnel alert reads the last host-side report instead.
This command is that reporter's seam: it runs the same readiness check the
Compose healthcheck runs on the ``cloudflared`` service (Section 16.1:
``cloudflared tunnel ready``) and stamps the result into the alert signal.

Usage (from a host-side cron, the Compose health bridge, or an operator):

    uv run --directory backend python manage.py report_tunnel_status
    uv run --directory backend python manage.py report_tunnel_status --up
    uv run --directory backend python manage.py report_tunnel_status --down

With neither flag the command probes the binary named by
``ORCHESTRATOR_CLOUDFLARED_BINARY`` (default ``cloudflared``) with the
``tunnel ready`` subcommand — the exact check Section 16.1 wires as the
container healthcheck — and records pass/fail. ``--up``/``--down`` force a
status without probing (for hosts where the binary is not on the caller's
PATH, e.g. a remote monitoring host); the choice is echoed so a forced value
is never mistaken for a probe result.
"""

from __future__ import annotations

import shutil
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.alerts import record_tunnel_status


class Command(BaseCommand):
    """Probe (or force) tunnel readiness and stamp the alert signal."""

    help = (
        "Report the cloudflared tunnel status into the MT-6.4-02 alert "
        "signal: probe `cloudflared tunnel ready` (Section 16.1's own "
        "healthcheck) or force --up/--down."
    )

    def add_arguments(self, parser) -> None:  # type: ignore[no-untyped-def]
        """``--up``/``--down`` force the status; default probes the binary."""
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--up",
            action="store_true",
            help="force an 'up' report without probing (e.g. remote reporter)",
        )
        group.add_argument(
            "--down",
            action="store_true",
            help="force a 'down' report without probing",
        )

    def handle(self, *args: object, **options: dict[str, object]) -> None:
        """Probe-or-force, stamp, and echo the recorded status."""
        if options["up"]:
            up, source = True, "forced (--up)"
        elif options["down"]:
            up, source = False, "forced (--down)"
        else:
            up, source = self._probe(), "probe"
        record_tunnel_status(up)
        self.stdout.write(
            self.style.SUCCESS(f"tunnel status recorded: {'up' if up else 'down'} ({source})")
        )

    def _probe(self) -> bool:
        """Run Section 16.1's exact healthcheck command; True iff it passes."""
        binary = getattr(settings, "CLOUDFLARED_BINARY", "cloudflared")
        if shutil.which(binary) is None:
            raise CommandError(
                f"{binary!r} not on PATH — use --up/--down to force a status, or set "
                "ORCHESTRATOR_CLOUDFLARED_BINARY (docs/plan/alerts.md, tunnel rule)."
            )
        result = subprocess.run(  # fixed argv, no shell
            [binary, "tunnel", "ready"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
