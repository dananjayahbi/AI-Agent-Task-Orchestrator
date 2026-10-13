"""MT-3.2-03 — authoritative patch parsing (Section 9.7; ADR-009).

Run with ``pytest backend/tests -k patch_parsing -q``. Pure unit tests
over :func:`apps.tasks.services.patch_parse.parse_unified_diff` —
hand-computed expectations, every format reading the module documents:

* multi-file git diffs (stats = the numstat definition),
* additions-only and deletions-only hunks,
* renames (counted once, under the new path),
* binary files (recorded, zero stats — no invented numbers),
* mode-only changes (header path only),
* hunk-body lines that *look* like file headers (``--- `` content),
* plain unified diffs with tab-timestamps,
* determinism (same bytes twice → identical output; ADR-009),
* the empty patch ("no changes" is valid, not an error),
* ``diff_summary.files == len(changed_files)`` on every fixture.

The oversize/degraded input lives in ``test_patch_artifacts`` end to
end; here the same parser proves it never cares where the bytes came
from (it is handed the received text either way — MT-3.2-02 drops the
*body*, never the parse).
"""

from __future__ import annotations

from apps.tasks.services.patch_parse import ParsedPatch, parse_unified_diff

# --- fixture: a realistic multi-file git diff --------------------------------

MULTI_FILE = """\
diff --git a/src/billing/invoice.py b/src/billing/invoice.py
index 1234567..89abcde 100644
--- a/src/billing/invoice.py
+++ b/src/billing/invoice.py
@@ -1,3 +1,4 @@
 def render():
-    return "old"
+    return "new"
+    return_flags = True
     return payload
diff --git a/docs/readme.md b/docs/readme.md
index aaa1111..bbb2222 100644
--- a/docs/readme.md
+++ b/docs/readme.md
@@ -10,2 +10,1 @@
 keep-this-line
-drop-this-line
diff --git a/src/billing/tax.py b/src/billing/tax.py
index ccc3333..ddd4444 100644
--- a/src/billing/tax.py
+++ b/src/billing/tax.py
@@ -7,3 +7,3 @@
 def rate():
-    return 0.19
+    return 0.20
     # TODO: regions
"""

ADDITIONS_ONLY = """\
diff --git a/new_file.py b/new_file.py
new file mode 100644
index 0000000..e69de29
--- /dev/null
+++ b/new_file.py
@@ -0,0 +1,3 @@
+line one
+line two
+line three
"""

DELETIONS_ONLY = """\
diff --git a/gone.py b/gone.py
deleted file mode 100644
index e69de29..0000000
--- a/gone.py
+++ /dev/null
@@ -1,3 +0,0 @@
-line one
-line two
-line three
"""

RENAME = """\
diff --git a/src/old_name.py b/src/new_name.py
similarity index 100%
rename from src/old_name.py
rename to src/new_name.py
"""

BINARY = """\
diff --git a/assets/logo.png b/assets/logo.png
index 4445556..7778889 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""

MODE_ONLY = """\
diff --git a/scripts/deploy.sh b/scripts/deploy.sh
old mode 100644
new mode 100755
"""

HUNK_LOOKS_LIKE_HEADER = """\
diff --git a/notes.txt b/notes.txt
--- a/notes.txt
+++ b/notes.txt
@@ -1,2 +1,2 @@
--- tricky deleted line
+++ tricky added line
 context stays
"""

PLAIN_UNIFIED = """\
--- a/src/x.py\t2026-10-11 09:00:00
+++ b/src/x.py\t2026-10-11 09:00:01
@@ -1 +1 @@
-old value
+new value
"""


def _assert_summary(parsed: ParsedPatch, files: int, insertions: int, deletions: int) -> None:
    summary = parsed.as_diff_summary()
    assert summary == {
        "files": files,
        "insertions": insertions,
        "deletions": deletions,
    }
    assert summary["files"] == len(parsed.changed_files)


def test_multi_file_diff_stats_match_hunk_content() -> None:
    """Three sections: hand-computed 3 files / 3 insertions / 3 deletions."""
    parsed = parse_unified_diff(MULTI_FILE)
    assert parsed.changed_files == (
        "src/billing/invoice.py",
        "docs/readme.md",
        "src/billing/tax.py",
    )
    # invoice.py: +2 / -1; readme.md: +0 / -1; tax.py: +1 / -1.
    _assert_summary(parsed, files=3, insertions=3, deletions=3)


def test_files_count_equals_changed_file_count() -> None:
    """diff_summary.files is len(changed_files) — R2/R6 input agreement."""
    parsed = parse_unified_diff(MULTI_FILE)
    assert parsed.files == len(parsed.changed_files) == 3


def test_additions_only_patch() -> None:
    """A new file: three insertions, no deletions, /dev/null on the old side."""
    parsed = parse_unified_diff(ADDITIONS_ONLY)
    assert parsed.changed_files == ("new_file.py",)
    _assert_summary(parsed, files=1, insertions=3, deletions=0)


def test_deletions_only_patch() -> None:
    """A deleted file: three deletions, no insertions, /dev/null on the new side."""
    parsed = parse_unified_diff(DELETIONS_ONLY)
    assert parsed.changed_files == ("gone.py",)
    _assert_summary(parsed, files=1, insertions=0, deletions=3)


def test_rename_counts_once_under_the_new_path() -> None:
    """No ---/+++ pair: the header's b-side wins, once (documented reading)."""
    parsed = parse_unified_diff(RENAME)
    assert parsed.changed_files == ("src/new_name.py",)
    _assert_summary(parsed, files=1, insertions=0, deletions=0)


def test_binary_file_recorded_with_zero_stats() -> None:
    """Binary sections are changed files with no line counts (7.2/9.7)."""
    parsed = parse_unified_diff(BINARY)
    assert parsed.changed_files == ("assets/logo.png",)
    _assert_summary(parsed, files=1, insertions=0, deletions=0)


def test_mode_only_change_recorded_from_the_header() -> None:
    """No hunks and no ---/+++ pair — the git header still names the file."""
    parsed = parse_unified_diff(MODE_ONLY)
    assert parsed.changed_files == ("scripts/deploy.sh",)
    _assert_summary(parsed, files=1, insertions=0, deletions=0)


def test_hunk_body_lines_that_look_like_headers_count_as_content() -> None:
    """``--- `` / ``+++ `` inside a hunk are stats, not new files."""
    parsed = parse_unified_diff(HUNK_LOOKS_LIKE_HEADER)
    assert parsed.changed_files == ("notes.txt",)
    _assert_summary(parsed, files=1, insertions=1, deletions=1)


def test_plain_unified_diff_with_tab_timestamps() -> None:
    """No git headers: the ---/+++ pair (timestamp stripped) carries the path."""
    parsed = parse_unified_diff(PLAIN_UNIFIED)
    assert parsed.changed_files == ("src/x.py",)
    _assert_summary(parsed, files=1, insertions=1, deletions=1)


def test_parsing_is_deterministic() -> None:
    """Same bytes twice → byte-identical output (ADR-009)."""
    first = parse_unified_diff(MULTI_FILE)
    second = parse_unified_diff(MULTI_FILE)
    assert first == second
    assert parse_unified_diff(MULTI_FILE.encode("utf-8")) == first


def test_empty_patch_is_no_changes_not_an_error() -> None:
    """The bridge's empty diff is legitimate: zero files, zero stats."""
    parsed = parse_unified_diff("")
    assert parsed.changed_files == ()
    _assert_summary(parsed, files=0, insertions=0, deletions=0)


def test_bytes_and_str_inputs_agree() -> None:
    """The stored bytes and their text decode to the same derivation."""
    assert parse_unified_diff(PLAIN_UNIFIED.encode("utf-8")) == parse_unified_diff(PLAIN_UNIFIED)
