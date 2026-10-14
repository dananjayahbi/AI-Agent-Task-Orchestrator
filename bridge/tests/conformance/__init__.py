"""WP-2.11 MCP client-compatibility conformance runner (MT-2.11-01; Sections 10.8, 10.9, 18).

The plan's "scripted client" (Section 18, MCP conformance row): a runner that
speaks MCP to the bridge exactly like an agent client, drives the full
Section 10.5 tool catalog for the coder / auditor / decomposer roles, and
emits the Section 10.9 client-compatibility matrix row plus per-check
pass/fail evidence.

Modules:

* :mod:`tests.conformance.connection` — stdio and streamable-HTTP MCP client
  connections plus the normalised :class:`~tests.conformance.connection.ToolCallResult`.
* :mod:`tests.conformance.checks` — the individual conformance checks
  (catalog, rules block, prompts, Section 9.2 catalog membership).
* :mod:`tests.conformance.scenarios` — the per-role tool flows.
* :mod:`tests.conformance.report` — the report model (matrix columns, checks,
  exit-code contract).
* :mod:`tests.conformance.runner` — orchestration plus the standalone CLI
  (``python -m tests.conformance.runner``; the invocation shape chosen by
  MT-2.11-01).

This package lives under ``bridge/tests/`` deliberately: the runner is test
infrastructure for measuring client compatibility, not shipped bridge code.
"""
