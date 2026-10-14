"""WP-6.2 restore drill — marker-count regression (MT-6.2-04 evidence gate).

The 2026-10-14 drill run failed its ``marker row restored`` check even
though the restore succeeded: Django's ``shell`` management command writes
an auto-import banner to **stdout** before executing ``-c`` code

    21 objects imported automatically (use -v 2 for details).

and the check compared the whole capture against ``"1"``. The real count
was the last line of the capture (``1``) — the drill misreported a passing
restore as a failure (see ``e2e/restore_drill_results.json`` findings and
``docs/plan/wp-6.2-restore-drill-2026-10-14.md``).

This suite pins the fix at both layers:

* :func:`e2e.restore_drill._last_output_line` parses the printed value
  out of a noisy capture (exact banner text from the failed run);
* the drill's marker query passes ``--no-imports`` so the banner is
  suppressed at the source instead of being parsed around.

Run: ``pytest backend/tests/test_restore_drill_marker_check.py -q``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
DRILL_PATH = REPO_ROOT / "e2e" / "restore_drill.py"

#: Exact stdout Django 5.2's shell command produced in the failed run
#: (e2e/restore_drill_results.json): banner, blank line, then the count.
FAILED_RUN_CAPTURE = "21 objects imported automatically (use -v 2 for details).\n\n1\n"


def _load_drill_module() -> ModuleType:
    """Import ``e2e/restore_drill.py`` (stdlib-only, no package layout)."""
    spec = importlib.util.spec_from_file_location("restore_drill_under_test", DRILL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_last_output_line_recovers_count_from_failed_run_capture() -> None:
    """The 2026-10-14 capture must parse to the restored count, not the banner."""
    drill = _load_drill_module()
    assert drill._last_output_line(FAILED_RUN_CAPTURE) == "1"


def test_last_output_line_handles_bare_and_empty_output() -> None:
    drill = _load_drill_module()
    assert drill._last_output_line("1\n") == "1"
    assert drill._last_output_line("1") == "1"
    assert drill._last_output_line("") == ""
    assert drill._last_output_line("   \n\n  ") == ""


def test_marker_query_disables_shell_auto_import_banner() -> None:
    """The marker count runs with --no-imports: no banner to parse at all."""
    source = DRILL_PATH.read_text(encoding="utf-8")
    assert '"--no-imports"' in source
    # The helper and its use in the smoke phase must both exist.
    assert "def _last_output_line(" in source
    assert "count = _last_output_line(raw_count)" in source
