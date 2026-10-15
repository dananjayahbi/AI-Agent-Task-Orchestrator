"""MT-6.3-01 — Board-load API scenario: the backend half of a 500-card board.

**Division of labor (recorded per the MT):** this script measures only
the API responses the board needs — five cursor pages of ``page_size=100``
= 500 cards (Section 13.4's board shape). The browser-side first-load
target (3 s) is owned by MT-4.11-04 (WP-4.11) and reported in
``docs/plan/web-performance-report.md`` — reused by cross-reference here,
never duplicated.

**Verdict basis:** there is no plan-side API NFR for board loads. The
results file judges the API total p95 against ``board.api_share_p95_ms``
from ``thresholds.json`` — a *derived* necessary condition for the
Section 13.4 web budget (if the API alone exceeds 3 s, the web target
cannot hold). It is labeled as derived, not an NFR, in the output.

Run: ``python e2e/perf/board_load.py --run-id 1``.
Execution instructions: ``docs/plan/perf-runbook.md``.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from perf_common import (
    Api,
    PerfError,
    judge,
    load_manifest,
    load_thresholds,
    summarize,
    verdict_line,
    write_results,
)
from seed_perf_fixture import DEFAULT_OWNER_PASSWORD


def fetch_board(
    api: Api, project_id: str, pages: int, page_size: int
) -> tuple[list[float], int, list[str]]:
    """Walk ``pages`` cursor pages; return (per-page ms, cards, page statuses)."""
    page_ms: list[float] = []
    statuses: list[str] = []
    cards = 0
    cursor: str | None = None
    for _ in range(pages):
        path = f"/projects/{project_id}/tasks?page_size={page_size}"
        if cursor:
            path += f"&cursor={cursor}"
        payload, status, ms = api.request("GET", path)
        page_ms.append(round(ms, 2))
        statuses.append(str(status))
        if status != 200 or not isinstance(payload, dict):
            break
        results = payload.get("results") or []
        cards += len(results)
        cursor = payload.get("next_cursor")
        if not cursor:
            break
    return page_ms, cards, statuses


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    thresholds = load_thresholds()
    parser = argparse.ArgumentParser(
        description="WP-6.3 board-load API scenario — 500-card data path (MT-6.3-01)."
    )
    parser.add_argument("--run-id", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--pages", type=int, default=5)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--project", default=None, help="project id (default: first seeded)")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--owner-username", default=None)
    parser.add_argument(
        "--cards",
        type=int,
        default=thresholds["scenario"]["board_cards"],
        help="cards the run must cover (Section 13.4 board shape)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = load_manifest(args.manifest)
    thresholds = load_thresholds()
    budget_ms = thresholds["board"]["api_share_p95_ms"]
    project_id = args.project or manifest["projects"][0]

    api = Api()
    api.login(
        args.owner_username or manifest["owner"]["username"],
        os.environ.get("PERF_OWNER_PASSWORD", DEFAULT_OWNER_PASSWORD),
    )

    all_pages: list[float] = []
    totals: list[float] = []
    cards_seen: list[int] = []
    statuses: list[str] = []
    for _ in range(args.iterations):
        page_ms, cards, page_statuses = fetch_board(api, project_id, args.pages, args.page_size)
        all_pages.extend(page_ms)
        cards_seen.append(cards)
        statuses.extend(page_statuses)
        totals.append(sum(page_ms))
        if any(status != "200" for status in page_statuses):
            break

    page_stats = summarize(all_pages)
    total_stats = summarize(totals)
    expected = args.cards
    shape_ok = bool(totals) and min(cards_seen) >= expected
    verdict = judge(total_stats["p95_ms"], budget_ms)
    verdict["basis"] = (
        "DERIVED necessary condition for Section 13.4's 3 s web first-load "
        "(web side: MT-4.11-04 / docs/plan/web-performance-report.md) — not an NFR"
    )
    verdict["pass"] = bool(verdict["pass"] and shape_ok)

    payload: dict[str, Any] = {
        "run_id": args.run_id,
        "iterations": len(totals),
        "project_id": project_id,
        "page_size": args.page_size,
        "pages_per_iteration": args.pages,
        "cards_per_iteration": sorted(set(cards_seen)),
        "expected_cards": expected,
        "shape_ok": shape_ok,
        "page_statuses": sorted(set(statuses)),
        "latency_ms": {"page": page_stats, "board_total": total_stats},
        "verdicts": {"board_api_total_p95_derived": verdict},
        "thresholds_source": "e2e/perf/thresholds.json (board.api_share_p95_ms, derived)",
        "division_of_labor": (
            "API side here (MT-6.3-01); browser side owned by MT-4.11-04 — "
            "cross-reference docs/plan/web-performance-report.md"
        ),
    }
    path = write_results(f"board_load_run{args.run_id}", payload)
    print(
        f"board_load run={args.run_id} iterations={len(totals)} "
        f"cards={sorted(set(cards_seen))} project={project_id}"
    )
    print(verdict_line("board_api_total_p95_derived", verdict))
    print(f"results: {path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PerfError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
