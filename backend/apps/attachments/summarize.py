"""Short summary generation per attachment (Section 9.5 stage 3; Sections 9.10, P10; MT-1.12-06).

Pluggable **interface with a disabled default** — Section 22's OQ-07
recorded default is *disabled*, and no generative provider is invented
before that owner decision (WP-1.13 territory). With the default
configuration the pipeline still completes: a **deterministic
extractive fallback** (head-of-document sentences under the configured
bound) summarises offline, so FR-ATT-03's ``short_description`` is
always populated for processed attachments.

Contracts:

* **Input is bounded** by ``ORCHESTRATOR_ATTACHMENT_SUMMARY_BUDGET_TOKENS``
  (chunks taken in sequence until the budget is spent) and **output** by
  ``ORCHESTRATOR_ATTACHMENT_SUMMARY_MAX_TOKENS`` — "short" is this
  documented bound, recorded in the changelog (MT-1.12-06: the plan
  says "short", not how short).
* **Untrusted content is data** (P10): the extractive fallback quotes
  the document's opening — it cannot follow instructions embedded in
  it. The prompt-injection fixture test proves the summary *quotes* the
  hostile text and executes nothing.
* **Provider failures degrade to the fallback**, never fail the
  pipeline (Section 9.5's description-provider degradation, applied to
  summaries by analogy — MT-1.12-06 risk note).
"""

from __future__ import annotations

import logging
import re
from typing import Final, Protocol, runtime_checkable

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .chunking import estimate_tokens, get_token_estimator
from .models import AttachmentChunk, TaskAttachment

logger = logging.getLogger(__name__)

#: Selector values accepted by ``ORCHESTRATOR_ATTACHMENT_SUMMARY_PROVIDER``.
#: ``disabled`` = no generative provider → deterministic fallback (default).
SUPPORTED_SUMMARY_PROVIDERS: Final[frozenset[str]] = frozenset({"disabled"})

#: Sentence boundary for the extractive fallback (documented choice).
_SENTENCE_SPLIT: Final = re.compile(r"(?<=[.!?])\s+")


@runtime_checkable
class SummaryProvider(Protocol):
    """Produce a short summary from bounded extracted text (Section 9.5)."""

    name: str

    def summarize(self, text: str, *, max_tokens: int) -> str:
        """Return a summary whose estimate is ≤ *max_tokens*.

        ``text`` is untrusted attachment content — treat it as data,
        never as instructions (P10).
        """
        ...


def extractive_summary(text: str, *, max_tokens: int) -> str:
    """Deterministic head-of-document fallback: opening sentences, bounded.

    Whitespace-normalised, then sentences accumulated in order while
    the configured estimator stays within *max_tokens*; a single
    over-long opening sentence is word-truncated to the bound. Empty
    input summarises to the empty string (nothing to describe).
    """
    flat = " ".join(text.split())
    if not flat:
        return ""
    estimator = get_token_estimator()
    chosen: list[str] = []
    used = 0
    for sentence in _SENTENCE_SPLIT.split(flat):
        if not sentence:
            continue
        cost = estimator(sentence)
        if not chosen and cost > max_tokens:
            words: list[str] = []
            for word in sentence.split():
                candidate = f"{' '.join(words)} {word}".strip()
                if estimator(candidate) > max_tokens:
                    break
                words.append(word)
            return " ".join(words)
        if used + cost > max_tokens:
            break
        chosen.append(sentence)
        used += cost
    return " ".join(chosen)


class DisabledSummaryProvider:
    """The OQ-07-style default: no generative model, extractive fallback."""

    name = "disabled"

    def summarize(self, text: str, *, max_tokens: int) -> str:
        """The documented deterministic fallback (offline completion)."""
        return extractive_summary(text, max_tokens=max_tokens)


def get_summary_provider() -> SummaryProvider:
    """The configured summary provider, fail-fast on unknown names (9.10)."""
    name = settings.ATTACHMENT_SUMMARY_PROVIDER
    if name == "disabled":
        return DisabledSummaryProvider()
    raise ImproperlyConfigured(
        f"ORCHESTRATOR_ATTACHMENT_SUMMARY_PROVIDER={name!r} is not implemented: "
        "no generative provider is invented before the OQ-07 owner decision "
        f"(supported: {sorted(SUPPORTED_SUMMARY_PROVIDERS)})."
    )


def bounded_summary_input(chunks: list[AttachmentChunk]) -> str:
    """Chunk text in sequence order, cut at the configured input budget.

    The Section 9.5 summary operates on a *bounded* context: chunks are
    taken from the start (most representative head of the document)
    until adding another would exceed
    ``ATTACHMENT_SUMMARY_BUDGET_TOKENS``; a first chunk larger than the
    whole budget is truncated to it.
    """
    budget = settings.ATTACHMENT_SUMMARY_BUDGET_TOKENS
    estimator = get_token_estimator()
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        cost = estimator(chunk.text)
        if not parts and cost > budget:
            truncated = extractive_summary(chunk.text, max_tokens=budget)
            parts.append(truncated)
            break
        if used + cost > budget:
            break
        parts.append(chunk.text)
        used += cost
    return "\n\n".join(parts)


def summarize_text(
    text: str, *, provider: SummaryProvider | None = None, max_tokens: int | None = None
) -> str:
    """Summarise *text* with the configured provider, clamped to the bound.

    Any provider failure logs its *type only* (Section 12.4 — never the
    text) and falls back to the deterministic summary, so a broken or
    cost-guarded remote call can never fail the pipeline (MT-1.12-06).
    """
    bound = max_tokens if max_tokens is not None else settings.ATTACHMENT_SUMMARY_MAX_TOKENS
    active = provider if provider is not None else get_summary_provider()
    if not text.strip():
        return ""
    try:
        summary = active.summarize(text, max_tokens=bound)
    except Exception as exc:  # degradation is the contract (Section 9.5)
        logger.warning("summary provider %r failed: %s", active.name, type(exc).__name__)
        summary = extractive_summary(text, max_tokens=bound)
    # Clamp regardless of provider: the bound is a contract, not a hint.
    if estimate_tokens(summary) > bound:
        summary = extractive_summary(text, max_tokens=bound)
    return summary


def apply_summary(attachment: TaskAttachment, chunks: list[AttachmentChunk]) -> str:
    """Summarise *attachment*'s chunks and persist FR-ATT-03's description."""
    summary = summarize_text(bounded_summary_input(chunks))
    attachment.description = summary
    attachment.save(update_fields=["description"])
    return summary


__all__ = [
    "SUPPORTED_SUMMARY_PROVIDERS",
    "DisabledSummaryProvider",
    "SummaryProvider",
    "apply_summary",
    "bounded_summary_input",
    "extractive_summary",
    "get_summary_provider",
    "summarize_text",
]
