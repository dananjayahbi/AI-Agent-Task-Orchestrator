"""Projects-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

The envelope handler (``apps/core/exceptions.py``) passes any DRF
``APIException`` whose ``default_code`` is already canonical straight
through, so these classes never invent a code — they name one that exists
in the closed 19-code catalog and choose the HTTP status that matches its
semantics.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import SERVER_ERROR


class PidSequenceExhausted(APIException):
    """Section 7.3 sequence exhaustion — a server-capacity failure.

    The project id sequence serves exactly 99,999 ids (``PID00001`` ..
    ``PID99999``). When the next value falls outside that span, allocation
    fails with a clear message instead of emitting a malformed id.

    **Code choice (MT-1.3-01's risk note, recorded in the changelog):**
    ``SERVER_ERROR`` — exhaustion is a server-side capacity condition, not
    anything a client's request can fix, so answering ``VALIDATION_ERROR``
    (which blames the input) would misdescribe the failure. No new code is
    invented; the catalog stays closed (Section 20.4 item 5).
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = SERVER_ERROR
    default_detail = (
        "Project id sequence exhausted: the PID capacity of 99,999 projects "
        "(Section 7.3) has been reached."
    )
