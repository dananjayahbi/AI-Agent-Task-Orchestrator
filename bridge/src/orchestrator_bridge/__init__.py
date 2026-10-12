"""MCP bridge and Merge Executor for the AI Agent Task Orchestrator (parent plan Section 10).

Launched through ``uv`` as a standalone Python package (Appendix A gives ``bridge/``
its own ``pyproject.toml``; no repo-root workspace exists) and speaking MCP with the
official MCP Python SDK (Section 6.6 technology decisions: "Python, ``uv``-managed,
official MCP Python SDK, packaged for one-line launch").

Architectural boundary: this package never imports from ``backend/`` or ``web/`` —
each package builds and versions independently in the monorepo (Appendix A;
independent-deployable rule referenced by MT-2.1-01), asserted by
``tests/test_layout.py``.
"""

__all__: list[str] = []
