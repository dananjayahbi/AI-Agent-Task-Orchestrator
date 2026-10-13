"""WP-1.15 coverage gate — per-module enforcement of the Section 18 target.

MT-1.15-05 turns the plan's prose target ("85% on state machine, leases, and
Policy Engine" — Section 18) into a CI-enforced invariant. coverage.py's own
``--fail-under`` guards a single *total*; the plan asks for a per-module
number so an unrelated low-coverage utility can never mask a regression in a
gated module and so a not-yet-existing module (the Policy Engine, WP-3.4)
cannot make the gate unpassable at M1. This script reads the JSON report a
gated pytest run writes and fails when **any** named module's line coverage
falls below the threshold.

Usage (the CI job and the documented local reproduction both run this):

    pytest --ds apps.core.settings.dev --cov=apps.tasks.state_machine \\
        --cov=apps.leases --cov-report=json:coverage-report.json -q
    python scripts/coverage_gate.py coverage-report.json \\
        apps.tasks.state_machine apps.leases --fail-under 85

The gated module set and the deferred Policy Engine portion are recorded in
the WP-1.15 changelog (Section 20.4 item 7); re-scope decisions belong there
too, not here.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def _module_files(files: dict[str, Any], module: str) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield (path, entry) for every report file under one dotted module.

    The report keys are the paths coverage measured — relative to the run's
    cwd on Linux CI, possibly backslash-separated or absolute on a host
    checkout — so the match is done on a normalized prefix at a path-segment
    boundary.
    """
    prefix = f"{module.replace('.', '/')}/"
    for path, entry in files.items():
        normalized = path.replace("\\", "/")
        index = normalized.find(prefix)
        if index == -1:
            continue
        if index > 0 and normalized[index - 1] != "/":
            continue
        yield normalized, entry


def main() -> int:
    """Enforce ``--fail-under`` on each module; print the gate table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="coverage JSON report path")
    parser.add_argument("modules", nargs="+", help="dotted module paths to gate")
    parser.add_argument("--fail-under", type=float, default=85.0)
    args = parser.parse_args()

    payload: dict[str, Any] = json.loads(args.report.read_text(encoding="utf-8"))
    files: dict[str, Any] = payload.get("files", {})
    if not files:
        print(f"{args.report} carries no measured files — run pytest with --cov", file=sys.stderr)
        return 2

    print(f"{'module':<28} {'stmts':>6} {'miss':>6} {'cover':>8}")
    failures: list[str] = []
    for module in args.modules:
        statements = covered = 0
        matched = 0
        for _path, entry in _module_files(files, module):
            matched += 1
            summary = entry["summary"]
            statements += int(summary["num_statements"])
            covered += int(summary["covered_lines"])
        if matched == 0 or statements == 0:
            print(
                f"{module}: no measured files — the module is absent from the report; "
                "fix the --cov arguments before trusting this gate",
                file=sys.stderr,
            )
            return 2
        percent = 100.0 * covered / statements
        print(f"{module:<28} {statements:>6} {statements - covered:>6} {percent:>7.1f}%")
        if percent < args.fail_under:
            failures.append(f"{module} ({percent:.1f}% < {args.fail_under:.0f}%)")

    if failures:
        print("", file=sys.stderr)
        print(
            "coverage gate FAILED: " + ", ".join(failures),
            file=sys.stderr,
        )
        print(
            "Section 18's target is behavioral — extend the owning suite with real "
            "transitions (never broaden tests just to move the number; MT-1.15-05 "
            "risk note) or record a re-scope in the WP-1.15 changelog.",
            file=sys.stderr,
        )
        return 1
    print(f"coverage gate passed (>= {args.fail_under:.0f}% on every gated module)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
