"""WP-1.10 performance package: the local SSE delivery/load check (MT-1.10-06).

Not the full WP-6.3 performance program (Section 18 layering) — one
deterministic publish-to-receipt measurement against the in-process ASGI
app, runnable in CI's unit layer without services.
"""
