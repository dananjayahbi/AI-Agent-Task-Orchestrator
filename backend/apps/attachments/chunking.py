"""Page/chunk splitting and token estimation (Section 9.5 stage 3; MT-1.12-05).

Turns a stage's :class:`ExtractionResult` into the WP-1.12 chunk model
rows — the retrieval pagination data of Section 9.5 ("split into pages
or token-bounded chunks, estimate tokens"):

* **Page-oriented outputs** (PDF pages, image OCR) keep page boundaries
  as numbered units: every chunk carries its 1-based ``page_number``,
  pages stay contiguous ``1..N``, and ``page_count`` on the attachment
  is ``total_pages`` — the data WP-1.14 serves with
  ``page_number``/``total_pages``.
* **Token-bounded chunks** — a page (or a page-less document: DOCX,
  Markdown, plain text) longer than the configured bound is split
  hierarchically (blank-line paragraphs → lines → words, with a final
  character slice for a pathological single token) so **no text is ever
  dropped**: coverage is a tested invariant (``" ".join(all chunk
  text) == " ".join(extracted text)`` after whitespace normalisation).
* **Token estimation** — a deterministic estimator, selected by the
  documented ``ORCHESTRATOR_ATTACHMENT_TOKEN_ESTIMATOR`` default
  ``chars_div_4`` (``ceil(chars / 4)``: the classic rough ratio; the
  plan fixes "estimate", not a tokenizer — a model-accurate tokenizer
  would be a new OQ, MT-1.12-05 risk note). Estimates are stored per
  chunk and rolled up to ``attachment.token_estimate`` (FR-ATT-03's
  descriptor field), equal to the sum of its chunks by construction.

Re-running the stage deletes and rebuilds the derived rows inside one
transaction — deterministic, replace-not-duplicate (Section 9.5
"derived data is re-creatable").
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from .models import AttachmentChunk, TaskAttachment

#: The only estimator implemented today; anything else fails fast
#: (Section 9.10 — a setting never silently degrades).
SUPPORTED_ESTIMATORS: Final[frozenset[str]] = frozenset({"chars_div_4"})

#: Characters per estimated token under the default method (documented
#: choice — MT-1.12-05 risk note: a choice, not a plan fact).
CHARS_PER_TOKEN: Final = 4

TokenEstimator = Callable[[str], int]


@dataclass(frozen=True)
class ExtractionResult:
    """One stage's extracted text, ready for splitting.

    Exactly one shape is populated: ``pages`` for the page-oriented
    path (PDF, images — a tuple even when a page is empty, so
    ``len(pages)`` is ``total_pages``), ``text`` for the token-bounded
    path (DOCX/Markdown/plain).
    """

    pages: tuple[str, ...] | None = None
    text: str = ""

    @property
    def is_page_based(self) -> bool:
        """Whether this result carries page boundaries."""
        return self.pages is not None

    def combined_text(self, *, page_separator: str = "\n\n") -> str:
        """All extracted text in order — the summary input (Section 9.5)."""
        if self.pages is not None:
            return page_separator.join(self.pages)
        return self.text


def chars_div_4(text: str) -> int:
    """``ceil(len(text) / 4)`` — the documented default estimator."""
    if not text:
        return 0
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def get_token_estimator() -> TokenEstimator:
    """The configured estimator, or a fail-fast error (Section 9.10)."""
    name = settings.ATTACHMENT_TOKEN_ESTIMATOR
    if name == "chars_div_4":
        return chars_div_4
    raise ImproperlyConfigured(
        f"Unknown ORCHESTRATOR_ATTACHMENT_TOKEN_ESTIMATOR {name!r}; "
        f"supported: {sorted(SUPPORTED_ESTIMATORS)}."
    )


def estimate_tokens(text: str) -> int:
    """Token estimate for *text* under the configured estimator."""
    return get_token_estimator()(text)


def _hard_split(token: str, max_tokens: int) -> list[str]:
    """Slice one pathological token so its pieces honour the bound."""
    width = max_tokens * CHARS_PER_TOKEN
    return [token[index : index + width] for index in range(0, len(token), width)]


def _pack(units: list[str], *, max_tokens: int, estimator: TokenEstimator) -> list[str]:
    """Greedily pack units into chunks whose estimate stays ≤ *max_tokens*."""
    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current} {unit}" if current else unit
        if current and estimator(candidate) > max_tokens:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def split_text(text: str, *, max_tokens: int | None = None) -> list[str]:
    """Split *text* into deterministic token-bounded chunks.

    Hierarchy: blank-line paragraphs → lines → words → character
    slices. Units larger than the bound are split *inside* themselves,
    so every chunk's estimate is ≤ the bound (a unit that fits whole is
    never broken). Nothing is dropped: every character of the input
    appears in some chunk (only whitespace between words is
    re-normalised — the tested coverage invariant).
    """
    bound = max_tokens if max_tokens is not None else settings.ATTACHMENT_CHUNK_MAX_TOKENS
    if bound < 1:
        raise ImproperlyConfigured("ORCHESTRATOR_ATTACHMENT_CHUNK_MAX_TOKENS must be ≥ 1.")
    estimator = get_token_estimator()
    if not text.strip():
        return []

    pieces: list[str] = []
    for paragraph in text.split("\n\n"):
        if estimator(paragraph) <= bound:
            pieces.append(paragraph)
            continue
        for line in paragraph.split("\n"):
            if estimator(line) <= bound:
                pieces.append(line)
                continue
            for word in line.split():
                if estimator(word) <= bound:
                    pieces.append(word)
                else:
                    pieces.extend(_hard_split(word, bound))
    # Whitespace-only units between separators vanish (coverage is
    # modulo separators — MT-1.12-05's own formulation).
    units = [unit for unit in (p.strip() for p in pieces) if unit]
    return _pack(units, max_tokens=bound, estimator=estimator)


def persist_chunks(attachment: TaskAttachment, result: ExtractionResult) -> list[AttachmentChunk]:
    """Replace *attachment*'s derived chunks and roll-ups (Section 9.5).

    One transaction: delete the previous derived set, insert the new
    rows, and stamp ``token_estimate`` (sum of chunks — FR-ATT-03) and
    ``page_count`` (number of pages for page-oriented results, ``None``
    for the token-bounded path). Deterministic on re-run: the same
    input yields byte-identical rows (MT-1.12-05 acceptance).
    """
    max_tokens = settings.ATTACHMENT_CHUNK_MAX_TOKENS
    rows: list[AttachmentChunk] = []
    sequence = 0
    page_count: int | None = None

    if result.is_page_based:
        pages = result.pages if result.pages is not None else ()
        page_count = len(pages)
        for page_number, page_text in enumerate(pages, start=1):
            for piece in split_text(page_text, max_tokens=max_tokens):
                rows.append(
                    AttachmentChunk(
                        attachment=attachment,
                        sequence=sequence,
                        page_number=page_number,
                        text=piece,
                        token_estimate=estimate_tokens(piece),
                    )
                )
                sequence += 1
    else:
        for piece in split_text(result.text, max_tokens=max_tokens):
            rows.append(
                AttachmentChunk(
                    attachment=attachment,
                    sequence=sequence,
                    page_number=None,
                    text=piece,
                    token_estimate=estimate_tokens(piece),
                )
            )
            sequence += 1

    total = sum(row.token_estimate for row in rows)
    with transaction.atomic():
        AttachmentChunk.objects.filter(attachment=attachment).delete()
        AttachmentChunk.objects.bulk_create(rows)
        TaskAttachment.objects.filter(pk=attachment.pk).update(
            token_estimate=total,
            page_count=page_count,
        )
    attachment.token_estimate = total
    attachment.page_count = page_count
    return rows


__all__ = [
    "CHARS_PER_TOKEN",
    "SUPPORTED_ESTIMATORS",
    "ExtractionResult",
    "TokenEstimator",
    "chars_div_4",
    "estimate_tokens",
    "get_token_estimator",
    "persist_chunks",
    "split_text",
]
