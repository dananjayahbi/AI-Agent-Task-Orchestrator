"""Authoritative unified-diff parsing — Section 9.7 (MT-3.2-03; FR-AUD-01).

One pure function over the *stored* patch bytes derives the two Section
7.2 resolution fields the rest of the system treats as truth:

* :func:`parse_unified_diff` → ``changed_files`` (repo-relative paths,
  one entry per changed file, first-seen order) and ``diff_summary``
  (``{files, insertions, deletions}`` counted from hunk content).

Discipline (each an explicit MT acceptance):

* **Server-side authority** — the bridge may send provisional
  ``changed_files``/``diff_summary`` (Section 10.5 captures them
  locally); this parse *replaces* them. Nothing merges or averages the
  two (Section 9.7; MT-3.2-03 risk note).
* **Deterministic (ADR-009)** — no clock, no I/O, no randomness: the
  same bytes produce the same output, so repeated runs are identical by
  construction.
* **Stats match hunk content** — insertions/deletions are counted from
  ``+``/``-`` body lines (the ``git diff --numstat`` definition), with
  hunk-header line counts tracking where hunks end so header-looking
  content lines are never miscounted.

Format readings, documented next to the fixtures (MT-3.2-03 risk note —
unified-diff edge cases are unspecified in the plan):

* **Git format wins when present** — the bridge uploads ``git diff``
  output (Section 9.7: branch vs. merge-base), whose ``diff --git a/x
  b/y`` header delimits every file section *including* mode-only changes
  and renames. Inside a section, the ``---``/``+++`` pair is preferred
  (handles spaces and quoting); otherwise the header's **b-side** is
  recorded — a rename counts once, under the new path (a counted
  reading, asserted in the fixtures).
* **Plain unified diffs** — sections are ``---``/``+++`` pairs; the pair
  only counts when both consecutive lines arrive together, and only
  outside a hunk (hunk-header counts track the boundary), so a hunk-body
  deletion of a line starting with ``--`` is counted as content, not
  mistaken for a file header.
* **Binary files** — recorded as changed with zero line stats (no hunk
  lines exist to count; MT-3.2-03 forbids inventing numbers).
* **Encoding** — UTF-8 with replacement on undecodable bytes: patches
  are byte blobs elsewhere (sha256 over raw bytes) and the parse never
  raises on content.

Oversize artifacts (Section 9.7's degraded path) still flow through this
parser — the *body* is dropped at storage time, never the parse (the
cap lives in ``services.resolutions``, MT-3.2-02).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

_GIT_HEADER: Final = re.compile(r'^diff --git (?:"?a/(?P<a>[^"]+)"?) (?:"?b/(?P<b>[^"]+)"?)$')
_HUNK_HEADER: Final = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")
_BINARY_LINE: Final = re.compile(r"^Binary files (?P<left>\S+) and (?P<right>\S+) differ$")


@dataclass(frozen=True)
class ParsedPatch:
    """The Section 7.2 ``changed_files`` + ``diff_summary`` derivation."""

    changed_files: tuple[str, ...]
    insertions: int
    deletions: int

    @property
    def files(self) -> int:
        """``diff_summary.files`` — equals the changed-file count (AC)."""
        return len(self.changed_files)

    def as_diff_summary(self) -> dict[str, int]:
        """The ``diff_summary`` JSON shape Section 7.2 fixes."""
        return {
            "files": self.files,
            "insertions": self.insertions,
            "deletions": self.deletions,
        }


def _strip_side(raw: str) -> str | None:
    """``a/x`` / ``b/x`` / tab-timestamp / ``/dev/null`` → a repo path.

    ``/dev/null`` returns ``None`` (that side of the pair is not a file);
    git's ``a/``/``b/`` prefixes and diff -u's trailing tab-timestamp are
    removed so paths are repo-root-relative (Section 12.3).
    """
    path = raw.strip()
    if "\t" in path:  # diff -u appends "\t<ctime>"
        path = path.split("\t", 1)[0]
    path = path.strip().strip('"')
    if path == "/dev/null":
        return None
    if path.startswith(("a/", "b/")):
        path = path[2:]
    return path or None


def _clean_header_side(raw: str) -> str:
    """Unquote one ``diff --git`` side (git quotes paths with spaces)."""
    if len(raw) >= 2 and raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1].replace('\\"', '"')
    return raw


def _hunk_counts(line: str) -> tuple[int, int]:
    """``(old_lines, new_lines)`` from a ``@@ -a,b +c,d @@`` header."""
    match = re.match(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@", line)
    if match is None:  # defensive: _HUNK_HEADER already matched
        return (1, 1)
    old = int(match.group(1)) if match.group(1) is not None else 1
    new = int(match.group(2)) if match.group(2) is not None else 1
    return (old, new)


def parse_unified_diff(patch: bytes | str) -> ParsedPatch:
    """Derive ``changed_files`` and ``diff_summary`` from *patch*.

    Pure and deterministic (Section 9.7: the backend computes these from
    the stored patch; ADR-009). Empty input is a legitimate "no changes"
    patch and yields empty lists and zero stats — not an error.
    """
    if isinstance(patch, bytes):
        text = patch.decode("utf-8", errors="replace")
    else:
        text = patch
    lines = text.splitlines()
    has_git_headers = any(line.startswith("diff --git ") for line in lines)

    changed: list[str] = []
    seen: set[str] = set()
    insertions = 0
    deletions = 0

    header_path: str | None = None  # b-side of the open git section
    section_recorded = False
    old_remaining = 0  # hunk-body lines left on each side (0 = outside)
    new_remaining = 0

    def record(path: str | None) -> None:
        nonlocal section_recorded
        if path is None or section_recorded:
            return
        section_recorded = True
        if path not in seen:
            seen.add(path)
            changed.append(path)

    def close_section() -> None:
        """Record the open section if nobody did; reset section state."""
        nonlocal header_path, section_recorded, old_remaining, new_remaining
        if not section_recorded and header_path is not None:
            record(header_path)
        header_path = None
        section_recorded = False
        old_remaining = 0
        new_remaining = 0

    index = 0
    while index < len(lines):
        line = lines[index]
        in_hunk = old_remaining > 0 or new_remaining > 0

        if not in_hunk and has_git_headers:
            git = _GIT_HEADER.match(line)
            if git is not None:
                close_section()
                header_path = _clean_header_side(git.group("b"))
                index += 1
                continue

        # ---/+++ pair: a file header only outside a hunk and only when
        # both consecutive lines agree (lookahead keeps a hunk-body
        # "-- ..." deletion from being mistaken for one).
        if not in_hunk and line.startswith("--- ") and index + 1 < len(lines):
            following = lines[index + 1]
            if following.startswith("+++ "):
                new_side = _strip_side(following[4:])
                old_side = _strip_side(line[4:])
                section_recorded = False  # a new section begins here
                record(new_side if new_side is not None else old_side)
                index += 2
                continue

        if not in_hunk:
            binary = _BINARY_LINE.match(line)
            if binary is not None:
                record(_strip_side(binary.group("right")) or _strip_side(binary.group("left")))
                index += 1
                continue

            if _HUNK_HEADER.match(line) is not None:
                old_remaining, new_remaining = _hunk_counts(line)
                # A zero-count side must not leave the hunk "open" on
                # its own (pure insertions/deletions count as ended when
                # both sides reach zero after the last body line).
                index += 1
                continue

            index += 1  # index/mode/similarity lines and blank prose
            continue

        # --- inside a hunk: count content, then track the boundary ----
        if line.startswith("+"):
            insertions += 1
            new_remaining -= 1
        elif line.startswith("-"):
            deletions += 1
            old_remaining -= 1
        elif line.startswith("\\"):  # "\ No newline at end of file"
            pass
        else:  # context (leading space or an empty line)
            old_remaining -= 1
            new_remaining -= 1
        index += 1

    close_section()
    return ParsedPatch(
        changed_files=tuple(changed),
        insertions=insertions,
        deletions=deletions,
    )


__all__ = ["ParsedPatch", "parse_unified_diff"]
