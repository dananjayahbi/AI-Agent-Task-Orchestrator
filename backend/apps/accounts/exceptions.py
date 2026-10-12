"""Accounts-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

The envelope handler (``apps/core/exceptions.py``) passes any DRF
``APIException`` whose ``default_code`` is already canonical straight
through, so these classes never invent a code — they name one that exists
in the closed 19-code catalog and choose the HTTP status that matches its
semantics.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException


class AuthForbiddenProject(APIException):
    """ADR-004 / G-07: the addressed project is outside the token's scope.

    Raised by the project-scope guard when a credential — resolved from the
    **token**, never the request body (Section 9.3 step 1) — targets another
    project's resource. 403 with the canonical ``AUTH_FORBIDDEN_PROJECT``
    code (WP-1.2 acceptance: a PID00001 agent token on a PID00002 resource).
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_code = "AUTH_FORBIDDEN_PROJECT"
    default_detail = "This token is not scoped to the addressed project."


class AuthRequired(APIException):
    """401 ``AUTH_REQUIRED`` for views that run with no authenticators.

    DRF's ``handle_exception`` downgrades its built-in ``NotAuthenticated`` /
    ``AuthenticationFailed`` to a **403** whenever the view cannot produce a
    ``WWW-Authenticate`` challenge — i.e. whenever ``authentication_classes``
    is empty, which is the case for ``POST /auth/login`` (the request
    *creates* the session; it presents no credential half of the time). The
    catalog answer for bad or missing credentials is the 401
    ``AUTH_REQUIRED`` (Section 9.2; MT-1.2-01's code set), so that endpoint
    raises this class instead: same canonical code, correct status, and no
    code invented — only the built-in coercion is bypassed.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "AUTH_REQUIRED"
    default_detail = "Authentication credentials are missing or invalid."
