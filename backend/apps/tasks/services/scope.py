"""Submission scope check against ``target_scope`` — Section 12.3 (MT-3.2-04).

A pure comparison: given a task's ``target_scope`` globs (Section 7.2)
and the **authoritative** ``changed_files`` parsed from the stored patch
(Section 9.7; MT-3.2-03), report every file that lies outside the scope.

Non-negotiable disciplines, each an explicit MT acceptance:

* **One matcher, not two** — every comparison goes through
  :func:`apps.projects.services.globs.glob_matches`, the shared
  matcher MT-3.1-03 fixed for the policy globs and WP-3.4's rules. This
  module imports it, never reimplements fnmatch semantics: a second
  implementation could let a "valid" glob mismatch at rule time (the
  exact failure the MT risk notes call out). The engine's Section 9.4
  recompute reads the same function, so the submission verdict and rule
  R2 can never disagree.
* **Section 12.3 path handling** — inputs are normalised repo-relative
  POSIX paths; anything that escapes the repo root (``..`` traversal,
  absolute paths, Windows drive letters), carries a backslash or NUL, or
  otherwise cannot be proven in-scope is **rejected as a violation
  rather than matched** (honest detection: never "match" a path the
  system cannot vouch for).
* **Authoritative input only** — the caller passes the resolution's
  parsed ``changed_files``; agent/auditor claims never enter this
  function (Section 9.7; Section 9.4 design note).
* **Fail-closed readings, recorded (Section 20.1 item 5):**

  * ``target_scope`` **empty → every changed file is a violation.**
    Section 12.3 makes scope enforcement honest: with no declared
    scope there is nothing a file can be shown to sit inside, so the
    submission escalates for human review (MT-3.2-04 risk note raised
    this as an open question; the strict reading matches G-06's
    mandatory-human-review posture — flagged as OQ in the WP
    changelog).
  * A stored glob that no longer parses (hand-edited row predating
    validation) also fails closed: an unverifiable scope claim cannot
    prove anything in-bounds.
  * A changed file that is itself unnormalisable (absolute, ``..``,
    backslash, NUL) is a violation regardless of globs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from apps.projects.services.globs import glob_matches

# Path-shape refusals (Section 12.3) — mirrored from the target-scope
# validator's rule set so one rule vocabulary spans validate/match.
_FORBIDDEN_CHARS = ("\\", "\x00")


@dataclass(frozen=True)
class ScopeVerdict:
    """The computed result both T8 and rule R2 read (never recomputed ad hoc)."""

    violations: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Clean when no changed file lies outside every scope glob."""
        return not self.violations

    def as_list(self) -> list[str]:
        """The offending paths for the response envelope (stable order)."""
        return list(self.violations)


def normalize_changed_path(raw: Any) -> str | None:
    """Normalise one changed-file path for matching; ``None`` = unusable.

    Rejects (returns ``None``) rather than sanitises: absolute paths
    (POSIX ``/x`` and Windows ``C:x``), backslashes, NUL, empty values
    and any ``..`` segment — Section 12.3: "normalized and rejected if
    they escape the repo root". ``./`` prefixes and interior
    ``a/../b`` collapses that stay inside the root are normalised, so a
    cosmetic ``./src/x.py`` still matches ``src/**``.
    """
    if not isinstance(raw, str):
        return None
    path = raw.strip()
    if not path:
        return None
    if any(char in path for char in _FORBIDDEN_CHARS):
        return None
    if path.startswith("/") or (len(path) >= 2 and path[1] == ":" and path[0].isalpha()):
        return None
    parts: list[str] = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if not parts:  # escapes the repo root
                return None
            parts.pop()  # interior climb that stays inside the root
            continue
        parts.append(segment)
    return "/".join(parts) or None


def evaluate_scope(
    target_scope: Sequence[str],
    changed_files: Iterable[Any],
) -> ScopeVerdict:
    """Flag every changed file outside every ``target_scope`` glob.

    ``target_scope`` comes from the task row (validated at creation,
    Section 12.3); ``changed_files`` is the resolution's parsed,
    authoritative list (Section 9.7). Pure: same inputs, same verdict.
    """
    globs = [glob for glob in target_scope if isinstance(glob, str) and glob]

    violations: list[str] = []
    for raw in changed_files:
        original = raw if isinstance(raw, str) else str(raw)
        path = normalize_changed_path(raw)
        if path is None:
            # Rejected input is a violation, never a match (12.3).
            violations.append(original)
            continue
        in_scope = False
        for pattern in globs:
            try:
                if glob_matches(pattern, path):
                    in_scope = True
                    break
            except ValueError:
                # An unparseable stored glob fails closed (recorded).
                continue
        if not in_scope:
            violations.append(original)
    return ScopeVerdict(violations=tuple(violations))


__all__ = ["ScopeVerdict", "evaluate_scope", "glob_matches", "normalize_changed_path"]
