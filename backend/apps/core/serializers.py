"""Typed response schemas for the generated OpenAPI contract (ADR-005).

The error envelope lives here once (Section 9.2 / MT-0.5-02's reusable-schema
obligation): every view that raises an error declares it through
``@extend_schema(responses={...: ErrorEnvelopeSerializer})`` so the document
shows one shared ``ErrorEnvelope`` component instead of a per-endpoint shape.
Field order mirrors the wire order fixed by :mod:`apps.core.errors`.

``StrictSerializerMixin`` also lives here since WP-1.4: the strict-input rule
(reject unknown keys — never silently ignore them) started app-local in
``projects`` and is shared now that a second app (``tasks``) needs it —
exactly the promotion ``projects/serializers/base.py`` announced when it was
written (MT-1.3-03; MT-1.4-03).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from rest_framework import serializers

from .errors import CANONICAL_ERROR_CODES


class StrictSerializerMixin(serializers.Serializer[Any]):
    """Reject unknown input keys with ``VALIDATION_ERROR`` (Section 9.2).

    DRF's default ``to_internal_value`` walks only the *declared* fields
    and drops everything else — which would make ``POST /projects`` silently
    ignore a client-supplied ``id`` (MT-1.3-03: "no client-supplied id is
    accepted" — rejecting proves it), make ``PATCH /projects/{pid}/policy``
    ignore a typo'd policy key (MT-1.3-04: "unknown field is rejected rather
    than ignored"), and — on ``tasks`` (MT-1.4-03) — let a PATCH smuggle
    ``state``/``lease_*`` past the writable-field allowlist and bypass
    WP-1.5's state machine. Read/render paths are unaffected — the check
    applies to writable input only.
    """

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """Validate declared fields only after proving every key is declared."""
        if isinstance(data, Mapping):
            declared = set(self.fields)
            unknown = sorted(key for key in data.keys() if str(key) not in declared)
            if unknown:
                raise serializers.ValidationError({str(key): "Unknown field." for key in unknown})
        return cast(dict[str, Any], super().to_internal_value(data))


class ErrorEnvelopeBodySerializer(serializers.Serializer[Any]):
    """The five Section 9.2 fields, in wire order, as they sit under ``error``."""

    code = serializers.ChoiceField(choices=CANONICAL_ERROR_CODES)
    message = serializers.CharField()
    retryable = serializers.BooleanField()
    details = serializers.DictField(required=False, allow_null=True)
    correlation_id = serializers.CharField()


class ErrorEnvelopeSerializer(serializers.Serializer[Any]):
    """The Section 9.2 wire envelope — five fields nested under ``error``.

    ``apps.core.errors.build_error_envelope`` emits the wrapper on the wire;
    the document must model that nesting, not a flat top-level body (the flat
    schema was a contract bug, fixed at the Wave 2 end-of-wave gate).
    """

    error = ErrorEnvelopeBodySerializer()
