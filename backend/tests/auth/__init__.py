"""MT-1.15-04 — the WP-1.15 authorization suite (Section 18 Security layer).

Adoption, not duplication (Section 19.6): MT-1.2-07's behavioral matrix stays
in ``tests/test_authorization_matrix.py`` — imported here by reference and run
in the same CI gate — while this package owns the *enumeration contract* that
suite does not carry:

* ``test_section_9_2_authorization.py`` — parses the parent plan's Section
  9.2 endpoint table at test time, ties every generated-OpenAPI operation to
  a row (or an explicit documented gap), forces each row to resolve or be
  deferred in the adopted ``DEFERRED_ENDPOINTS`` guard, and links every row
  to the test that behaviorally proves its caller cells.
* ``test_attachment_access_paths.py`` — the rest of MT-1.2-07's negative-path
  quartet (malformed / unknown / expired tokens) on the WP-1.13/1.14
  attachment access paths, plus the auditor and merge-executor read cells of
  the Section 9.2 "Owner / Agent (read)" column.
* ``test_feature_flag_token_behavior.py`` — closes the MT-1.2-01 feature-flag
  follow-up for the flag seam that exists at M1 (WP-0.5
  ``ORCHESTRATOR_FEATURE_FLAGS``); the ``AUTH_MODE=oidc`` live matrix stays
  explicitly deferred to WP-1.3.

Run: ``pytest backend/tests/auth -v`` (MT-1.15-04 test command); the combined
WP-1.15 gate command lives in CONTRIBUTING.md and the ``coverage-gate`` job
of ``.github/workflows/test.yaml``.
"""
