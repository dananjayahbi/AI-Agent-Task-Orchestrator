"""Cursor pagination helpers (Section 9.2; conventions/pagination.md; MT-0.5-04).

The one implementation of the v1 list convention: an opaque ``cursor``, the
canonical two-member envelope (``results`` + ``next_cursor``), documented
defaults of 25 items per page capped at 100 (WP-0.5 documented choices, not
plan facts), and stable ordering.

Ordering for token-shaped rows: this helper pages by primary key —
``BigAutoField`` ids are monotonic, so ``-pk`` (newest first) is a stable,
deterministic sort with the Section 7.3 identifier as the order itself.
String-keyed Section 7.3 ids (projects — ``PID`` + five zero-padded
digits) page through :func:`string_id_cursor_page`: lexicographic order on
the padded rendering *is* generation order, the documented sort of
``GET /projects``. Task ids need care beyond three digits (``T1000``);
their list endpoint supplies its own sort when it lands (pagination.md
rule 2). The cursor encoding below stays reusable for any string or int
key.
"""

from __future__ import annotations

import base64
import binascii

from django.db.models import Model, QuerySet
from rest_framework.exceptions import ValidationError

# pagination.md documented defaults (WP-0.5 choices, flagged as such there).
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def parse_page_size(raw: str | int | None) -> int:
    """Clamp ``page_size`` to ``1..MAX_PAGE_SIZE`` (endpoint documents this).

    Clamping (rather than rejecting) is the documented per-endpoint choice
    for token lists: a too-large page is a client hint, not an error — the
    RISK-13 cap is a server guarantee either way.
    """
    if raw is None:
        return DEFAULT_PAGE_SIZE
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError("page_size must be an integer.") from exc
    return max(1, min(value, MAX_PAGE_SIZE))


def encode_cursor(key: int | str) -> str:
    """Encode a cursor value opaquely (clients never parse it — rule 1)."""
    raw = str(key).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> int | None:
    """Decode an opaque cursor back to a page key; ``None`` = first page.

    A malformed cursor is a client error drawn from the catalog:
    DRF ``ValidationError`` → ``VALIDATION_ERROR`` (Section 20.4 item 5).
    """
    if cursor is None or cursor == "":
        return None
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        key = int(decoded)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValidationError("Invalid cursor.") from exc
    return key


def decode_str_cursor(cursor: str | None) -> str | None:
    """Like :func:`decode_cursor` for string-keyed lists (Section 7.3 ids).

    Project ids are ``PID`` + five zero-padded digits (Section 7.3), so
    lexicographic order *is* generation order — a single stable string key
    pages the registry deterministically (pagination.md rule 2; the
    documented sort of ``GET /projects``).
    """
    if cursor is None or cursor == "":
        return None
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValidationError("Invalid cursor.") from exc


def id_cursor_page[ModelT: Model](
    queryset: QuerySet[ModelT],
    *,
    cursor: int | None,
    page_size: int,
    descending: bool = True,
) -> tuple[list[ModelT], str | None]:
    """One page of *queryset* keyed by primary key + its ``next_cursor``.

    Fetches ``page_size + 1`` rows so end-of-list is detectable without a
    count: ``next_cursor`` is ``None`` exactly when the page is the last one
    (clients stop on that signal alone — pagination.md).
    """
    ordered = queryset.order_by("-pk" if descending else "pk")
    if cursor is not None:
        condition = {"pk__lt": cursor} if descending else {"pk__gt": cursor}
        ordered = ordered.filter(**condition)
    rows = list(ordered[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_cursor(rows[-1].pk) if has_more and rows else None
    return rows, next_cursor


def string_id_cursor_page[ModelT: Model](
    queryset: QuerySet[ModelT],
    *,
    cursor: str | None,
    page_size: int,
    ascending: bool = True,
) -> tuple[list[ModelT], str | None]:
    """One page of *queryset* keyed by its string primary key + cursor.

    The string-key sibling of :func:`id_cursor_page` for Section 7.3 ids
    whose zero-padded rendering makes lexicographic order the generation
    order (``GET /projects`` — pagination.md rule 2's documented sort).
    ``ascending`` matches that generation order by default; callers paging
    newest-first pass ``ascending=False``. Same fetch-one-lookahead and
    ``next_cursor is None`` end-of-list contract.
    """
    ordered = queryset.order_by("pk" if ascending else "-pk")
    if cursor is not None:
        condition = {"pk__gt": cursor} if ascending else {"pk__lt": cursor}
        ordered = ordered.filter(**condition)
    rows = list(ordered[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_cursor(rows[-1].pk) if has_more and rows else None
    return rows, next_cursor
