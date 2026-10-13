"""MT-3.2-04 — scope violation check against ``target_scope`` (Section 12.3).

Run with ``pytest backend/tests -k scope_check -q``. Pure unit tests
over :func:`apps.tasks.services.scope.evaluate_scope`:

* clean in-scope submission (no violations),
* one out-of-scope file flagged **with its path**,
* directory-prefix and extension glob edge cases (anchored matching),
* traversal / absolute / backslash inputs rejected rather than matched
  (Section 12.3),
* ``./`` and interior ``a/../b`` normalisation,
* the recorded empty-``target_scope`` reading (fail-closed — every
  changed file violates; raised as an OQ in the WP changelog),
* the invalid-stored-glob fail-closed reading,
* **one matcher**: the module uses ``globs.glob_matches`` itself, not a
  second implementation (the MT's "no second matcher" acceptance —
  asserted by object identity, so a future fork fails this test).
"""

from __future__ import annotations

from apps.projects.services import globs
from apps.tasks.services import scope


def test_in_scope_patch_is_clean() -> None:
    """Files under ``src/**`` with that scope declared: no violations."""
    verdict = scope.evaluate_scope(
        ["src/**"],
        ["src/billing/invoice.py", "src/billing/tax.py"],
    )
    assert verdict.ok is True
    assert verdict.violations == ()
    assert verdict.as_list() == []


def test_single_out_of_scope_file_is_flagged_with_its_path() -> None:
    """One offender, captured verbatim for review_reason scope_violation."""
    verdict = scope.evaluate_scope(
        ["src/**"],
        ["src/billing/invoice.py", "lib/rogue.py"],
    )
    assert verdict.ok is False
    assert verdict.violations == ("lib/rogue.py",)
    assert verdict.as_list() == ["lib/rogue.py"]


def test_directory_prefix_glob_matches_only_its_segment() -> None:
    """``src/*`` is one segment deep (anchored fnmatch semantics)."""
    assert scope.evaluate_scope(["src/*"], ["src/invoice.py"]).ok is True
    verdict = scope.evaluate_scope(["src/*"], ["src/billing/invoice.py"])
    assert verdict.violations == ("src/billing/invoice.py",)


def test_recursive_glob_matches_below_the_prefix() -> None:
    """``src/**`` walks every depth — the recursive operator's reading."""
    verdict = scope.evaluate_scope(["src/**"], ["src/billing/deep/nested/module.py"])
    assert verdict.ok is True


def test_extension_glob_is_anchored_to_the_repo_root() -> None:
    """``*.py`` matches only root-level files — repo-relative anchoring."""
    assert scope.evaluate_scope(["*.py"], ["main.py"]).ok is True
    verdict = scope.evaluate_scope(["*.py"], ["src/main.py"])
    assert verdict.violations == ("src/main.py",)


def test_union_of_globs_any_match_is_in_scope() -> None:
    """A file inside *any* glob is clean; outside *every* glob violates."""
    verdict = scope.evaluate_scope(
        ["src/**", "docs/**"],
        ["docs/readme.md", "src/a.py", "infra/deploy.yml"],
    )
    assert verdict.violations == ("infra/deploy.yml",)


def test_traversal_path_is_rejected_not_matched() -> None:
    """``..`` never matches — Section 12.3: rejected rather than matched."""
    verdict = scope.evaluate_scope(["**"], ["../etc/passwd", "src/../../escape.py"])
    assert verdict.ok is False
    assert set(verdict.violations) == {"../etc/passwd", "src/../../escape.py"}


def test_absolute_paths_are_rejected() -> None:
    """POSIX and Windows-drive absolutes never match (Section 12.3)."""
    verdict = scope.evaluate_scope(["**"], ["/etc/passwd", "C:/Windows/system.ini"])
    assert verdict.violations == ("/etc/passwd", "C:/Windows/system.ini")


def test_backslash_and_nul_inputs_are_rejected() -> None:
    """POSIX paths only: backslash and NUL are refusals, not separators."""
    verdict = scope.evaluate_scope(["**"], ["src\\billing\\invoice.py", "src/a\x00py"])
    assert verdict.violations == ("src\\billing\\invoice.py", "src/a\x00py")


def test_dot_slash_and_interior_climb_normalise_before_matching() -> None:
    """Cosmetic ``./`` and interior ``..`` collapse; the glob still sees sense."""
    verdict = scope.evaluate_scope(
        ["src/**"],
        ["./src/a.py", "src/billing/../billing/tax.py"],
    )
    assert verdict.ok is True, verdict.violations


def test_empty_target_scope_is_fail_closed_every_file_violates() -> None:
    """Recorded reading (MT-3.2-04 risk note; OQ in the changelog).

    With no declared scope nothing can be shown to sit inside it, so
    every changed file escalates — G-06's honest-enforcement posture.
    An *empty change set* under an empty scope stays clean (there is no
    file to violate).
    """
    verdict = scope.evaluate_scope([], ["src/a.py"])
    assert verdict.ok is False
    assert verdict.violations == ("src/a.py",)
    assert scope.evaluate_scope([], []).ok is True


def test_invalid_stored_glob_fails_closed() -> None:
    """A stored glob that cannot parse proves nothing — escalation wins."""
    verdict = scope.evaluate_scope(["a**b"], ["src/a.py"])
    assert verdict.ok is False
    assert verdict.violations == ("src/a.py",)


def test_non_string_changed_entries_are_violations() -> None:
    """Unnormalisable input is refused, never silently coerced into scope."""
    verdict = scope.evaluate_scope(["**"], [None, 42])
    assert verdict.violations == ("None", "42")


def test_the_single_shared_matcher_is_used_verbatim() -> None:
    """No second matcher (MT-3.2-04 acceptance): identity, not equivalence.

    ``scope.glob_matches`` *is* ``apps.projects.services.globs.glob_matches``
    — the same object the policy-glob validation and WP-3.4's rules call,
    so validate/match/rule can never disagree (MT-3.1-03's risk note).
    """
    assert scope.glob_matches is globs.glob_matches
