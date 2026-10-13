"""Repo-relative glob validation and the single shared matcher (Section 12.3).

One module, two responsibilities, deliberately coupled (MT-3.1-03 risk
note): *validation* ("is this glob well-formed?") and *matching* ("does
this path match?") share one translation, so a glob that validates can
never fail to match at rule time for syntax reasons. WP-3.4's Policy
Engine rules R3/R4/R5 and the WP-3.2 submission scope check must import
:func:`glob_matches` / :func:`glob_to_regex` from here rather than
reimplementing fnmatch semantics — two implementations would let a
"valid" glob silently mismatch later (the exact failure mode the MT
risk notes call out).

Syntax (documented here because the plan fixes the discipline, not the
grammar — a reading recorded in the WP changelog, Section 20.1 item 5):

* ``*``   — any run of characters **within one path segment**;
* ``**``  — the recursive operator, only as a **whole path segment**
  (``**/a``, ``a/**/b``, ``a/**``); any other use (``a**b``, ``***``)
  is a syntax error rather than a silent degradation to ``*``;
* ``?``   — exactly one character within a segment;
* ``[...]`` — character class (``[abc]``, ``[a-z]``, ``[!abc]`` negated);
  an unterminated class is a syntax error;
* every other character is literal.

Matching is anchored: the whole repo-relative POSIX path must match.
Path rules (Section 12.3): globs are repo-root-relative — no absolute
paths, no ``..`` traversal segments, no backslashes, no NUL — the same
concrete rules ``apps.tasks.services.tasks.validate_target_scope_globs``
applies to task ``target_scope`` (that helper predates this module and
carries the identical rules; folding it onto this shared module is a
noted follow-up, not a WP-3.1 change).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from rest_framework.exceptions import ValidationError

# Section 12.3 discipline, same caps as target_scope (one rule set): a
# policy glob list is a bounded, path-shaped allowlist — not a program.
_MAX_GLOBS_PER_LIST = 64
_MAX_GLOB_LENGTH = 500

# Characters that must never appear in a repo-relative glob: backslash
# (paths are POSIX; an escape character would make matching ambiguous)
# and NUL (cannot occur in a path, truncates C-level strings).
_FORBIDDEN_CHARS = {
    "\\": "must use forward slashes, not backslashes",
    "\x00": "must not contain NUL",
}


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate one glob into an anchored regex — **the** matcher.

    Raises ``ValueError`` for unparseable syntax (``**`` outside a whole
    segment, unterminated ``[`` class, or a class body that cannot form a
    valid regex class); callers validating user input surface that as a
    per-entry problem, callers matching trusted (validated) input may let
    it propagate — it indicates a bug, not user error.
    """
    out: list[str] = ["\\A"]
    index = 0
    length = len(pattern)
    while index < length:
        char = pattern[index]
        if char == "*":
            run_end = index
            while run_end < length and pattern[run_end] == "*":
                run_end += 1
            stars = run_end - index
            if stars == 1:
                out.append("[^/]*")
                index = run_end
                continue
            # A run of two or more stars is the recursive operator only as
            # a whole path segment: start-of-pattern or after '/', and
            # end-of-pattern or before '/'. Anything else is refused
            # outright — silently degrading '**' to '*' is exactly the
            # validate/match divergence the single-matcher rule forbids.
            segment_start = index == 0 or pattern[index - 1] == "/"
            segment_end = run_end == length or pattern[run_end] == "/"
            if stars > 2 or not (segment_start and segment_end):
                raise ValueError("'**' must occupy a whole path segment")
            if run_end < length and pattern[run_end] == "/":
                # '**/' matches zero or more leading segments, so
                # '**/security.py' matches a repo-root file too.
                out.append("(?:[^/]+/)*")
                index = run_end + 1
            else:
                out.append(".*")  # trailing '**': everything below
                index = run_end
            continue
        if char == "?":
            out.append("[^/]")
            index += 1
            continue
        if char == "[":
            cursor = index + 1
            if cursor < length and pattern[cursor] in "!^":
                cursor += 1
            if cursor < length and pattern[cursor] == "]":
                cursor += 1  # a leading ']' is a literal member
            while cursor < length and pattern[cursor] != "]":
                cursor += 1
            if cursor >= length:
                raise ValueError("unterminated '[' character class")
            body = pattern[index + 1 : cursor]
            negated = body[:1] in {"!", "^"}
            if negated:
                body = body[1:]
            out.append(f"[{'^' if negated else ''}{body}]")
            index = cursor + 1
            continue
        out.append(re.escape(char))
        index += 1
    out.append("\\Z")
    try:
        return re.compile("".join(out))
    except re.error as exc:  # e.g. a bad range like '[z-a]' inside a class
        raise ValueError(f"invalid character class: {exc}") from exc


def glob_matches(pattern: str, path: str) -> bool:
    """Does the repo-relative POSIX *path* match *pattern*? (anchored).

    ``pattern`` must already be validated (``glob_to_regex`` raises on
    syntax errors); ``path`` is normalized by the caller — the matcher
    does no IO and never resolves symlinks (Section 12.3: symlink
    escaping is enforced on payload paths upstream, detected at audit
    time here).
    """
    return glob_to_regex(pattern).match(path) is not None


def validate_glob_list(globs: Iterable[Any], *, field: str | None = None) -> list[str]:
    """Validate one policy glob list; return the cleaned entries.

    Raises the DRF ``ValidationError`` the envelope handler maps to the
    catalog's ``VALIDATION_ERROR`` with per-index ``details`` — never a
    500, never a silently accepted escape pattern (Section 12.3;
    MT-3.1-03). ``field`` keys the payload by field name for standalone
    or object-level callers (``{field: {index: [problems]}}``); serializer
    *field* validators pass ``field=None`` because DRF already keys a
    per-field ``ValidationError`` under that field's name — supplying it
    there would double-wrap. Either way the per-index shape matches the
    target-scope validator in ``apps.tasks`` (one convention, one
    matcher).
    """
    cleaned: list[str] = []
    errors: dict[str, list[str]] = {}
    entries = list(globs)
    if len(entries) > _MAX_GLOBS_PER_LIST:
        message = f"At most {_MAX_GLOBS_PER_LIST} globs."
        raise ValidationError({field: message} if field else message)
    for position, raw in enumerate(entries):
        if not isinstance(raw, str):
            errors[str(position)] = ["Each glob must be a string."]
            continue
        glob = raw.strip()
        problems: list[str] = []
        if not glob:
            problems.append("must not be empty")
        if len(glob) > _MAX_GLOB_LENGTH:
            problems.append(f"must be at most {_MAX_GLOB_LENGTH} characters")
        for char, message in _FORBIDDEN_CHARS.items():
            if char in glob:
                problems.append(message)
        if glob.startswith("/") or (len(glob) >= 2 and glob[1] == ":" and glob[0].isalpha()):
            problems.append("must be relative to the repo root (not absolute)")
        segments = set(glob.split("/"))
        if ".." in segments:
            problems.append("must not traverse outside the repo root ('..')")
        if not problems:
            try:
                glob_to_regex(glob)
            except ValueError as exc:
                problems.append(f"invalid glob syntax ({exc})")
        if problems:
            errors[str(position)] = problems
        else:
            cleaned.append(glob)
    if errors:
        raise ValidationError({field: errors} if field else errors)
    return cleaned


__all__ = ["glob_matches", "glob_to_regex", "validate_glob_list"]
