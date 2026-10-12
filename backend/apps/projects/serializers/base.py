"""Shared serializer behavior for the projects app (MT-1.3-03/04).

The strict-input rule moved to ``apps.core.serializers`` when WP-1.4's
tasks app became its second consumer (MT-1.4-03 — the promotion this
module announced). The name is re-exported here so every projects import
and test keeps working unchanged.
"""

from __future__ import annotations

from apps.core.serializers import StrictSerializerMixin

__all__ = ["StrictSerializerMixin"]
