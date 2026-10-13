"""Untrusted-content banner for attachment-derived text (P10; Section 9.5;
MT-1.14-04).

Section 9.5: *"All text outputs are prefixed with an untrusted-content
banner (P10)"*; FR-ATT-04 closes the same loop — *"all such text is
prefixed with the untrusted-content banner before delivery."* An
attacker-controlled file must not become trusted instructions inside a
model's context; the banner tells the model the content is data, not
commands.

Recorded decisions (MT-1.14-04 risk notes):

* **One layer: delivery only.** The banner is applied at the content
  endpoint boundary — never stored (the cache of MT-1.13-04 holds
  un-decorated text) and never pre-applied at generation. Every text
  field of a delivered payload is passed through
  :func:`mark_untrusted` exactly once per response; the helper is
  idempotent (an already-prefixed value is returned unchanged), so a
  future source that *did* store decorated text cannot double-prefix.
* **Short-metadata exemption.** Descriptor ``short_description`` in
  task/list payloads (MT-1.14-01) stays **unbannered short metadata** —
  the reading MT-1.14-04's risk note offers, asserted in the banner
  suite: it is a bounded summary, list views would gain banner noise
  per row, and the exact-value contract was locked by WP-1.11's
  descriptor tests. Full text (transcripts, layout descriptions,
  markdown pages) is always bannered.
* **Banner text is configuration** (``ORCHESTRATOR_ATTACHMENT_
  UNTRUSTED_BANNER``; Section 9.10 / configuration.md) with one
  documented default — no environment-specific content (plan 20.4 item
  3), no secrets. The bridge (WP-2.5) reads the same REST payload, so
  the backend and bridge agree who applies the banner on each path:
  here for REST, the bridge adds none for the same text (P10
  coordination note).
* **Errors are not text payloads** — the Section 9.2 envelope never
  carries the banner (MT-1.14-04 out-of-scope; MT-1.14-05).
"""

from __future__ import annotations

from django.conf import settings


def untrusted_banner() -> str:
    """The configured banner text (Section 9.10 setting).

    The documented default lives with the setting in
    ``apps.core.settings.base`` (one source; configuration.md records
    it) — this module never hardcodes banner text.
    """
    return settings.ATTACHMENT_UNTRUSTED_BANNER


def mark_untrusted(text: str) -> str:
    """Prefix *text* with the untrusted-content banner — exactly once.

    Empty input returns unchanged (nothing to mark); an already-prefixed
    value is returned as-is (idempotence is the duplicate-banner guard,
    tested).
    """
    if not text:
        return text
    banner = untrusted_banner()
    if text.startswith(banner):
        return text
    return f"{banner}\n{text}"


__all__ = ["mark_untrusted", "untrusted_banner"]
