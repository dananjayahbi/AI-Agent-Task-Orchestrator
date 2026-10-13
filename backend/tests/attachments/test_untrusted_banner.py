"""MT-1.14-04 — the untrusted-content banner on every delivered text (P10).

Run with ``pytest backend/tests/attachments/test_untrusted_banner.py -v``.

Proves:

* every text-returning format is banner-prefixed at the delivery
  boundary — ``text_ocr`` (transcript *and* description), ``markdown``
  pages, text-safe ``auto``;
* exactly one banner per delivered text value, per page of a
  multi-page document, across repeated retrievals (no double-prefix of
  the cached description — the store stays un-decorated);
* ``image_base64`` payloads are never prefixed (binary, not text);
* the banner text is configuration (``ATTACHMENT_UNTRUSTED_BANNER``),
  not hardcoded environment-specific content (plan 20.4 item 3);
* the descriptor ``short_description`` in task payloads stays the
  documented short-metadata exemption (asserted either way — the
  MT-1.14-04 decision, recorded in the WP changelog);
* the helper is the one choke point: idempotent, and the error path
  (MT-1.14-05) never carries it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.attachments.banner import mark_untrusted, untrusted_banner

from .helpers import (
    MARKDOWN_BYTES,
    envelope_code,
    make_project,
    make_task,
    owner_client,
    png_bytes,
    process_ready,
)

pytestmark = pytest.mark.django_db

CONTENT_URL = "/api/v1/attachments/{attachment_id}/content?{query}"
TASK_URL = "/api/v1/tasks/{task_id}"

TRANSCRIPT = "banner subject transcript"


@pytest.fixture(autouse=True)
def media_root(tmp_path: Path) -> Any:
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


@pytest.fixture
def owner() -> APIClient:
    return owner_client()


def _banner_count(text: str) -> int:
    return text.count(untrusted_banner())


# --- helper contract (the one choke point) -----------------------------------


def test_mark_untrusted_prefixes_once_and_is_idempotent() -> None:
    """Exactly one banner even when a source repeats the call (risk note)."""
    once = mark_untrusted("original text")
    assert once == f"{untrusted_banner()}\noriginal text"
    assert mark_untrusted(once) == once  # cached-decorated input cannot double


def test_mark_untrusted_leaves_empty_input_alone() -> None:
    """Nothing delivered, nothing marked (an empty page carries no banner)."""
    assert mark_untrusted("") == ""


def test_banner_text_is_configuration() -> None:
    """The banner reads from the Section 9.10 setting (plan 20.4 item 3)."""
    with override_settings(ATTACHMENT_UNTRUSTED_BANNER="[CUSTOM] data only"):
        assert untrusted_banner() == "[CUSTOM] data only"
        assert mark_untrusted("x") == "[CUSTOM] data only\nx"


# --- every delivered text value (FR-ATT-04; Section 9.5 P10) -----------------


def test_text_ocr_banners_transcript_and_description(owner: APIClient, task: Any) -> None:
    from apps.attachments.models import TaskAttachment

    attachment = process_ready(task, png_bytes(), name="shot.png", transcript=TRANSCRIPT)
    TaskAttachment.objects.filter(pk=attachment.pk).update(
        layout_caption="Layout: a title and two buttons."
    )
    body = cast(
        dict[str, Any],
        owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=text_ocr")).json(),
    )

    assert body["content"].startswith(untrusted_banner())
    assert TRANSCRIPT in body["content"]
    assert body["description"].startswith(untrusted_banner())
    assert _banner_count(body["content"]) == 1
    assert _banner_count(body["description"]) == 1


def test_markdown_pages_carry_exactly_one_banner_each(owner: APIClient, task: Any) -> None:
    """One banner per delivered page, not once per response (per-page rule)."""
    from apps.attachments.models import AttachmentChunk

    long_markdown = ("\n\n".join(f"Para {i} " + "word " * 150 for i in range(12))).encode()
    attachment = process_ready(task, long_markdown, name="long.md")
    total = AttachmentChunk.objects.filter(attachment=attachment).count()
    assert total > 1

    for page in range(1, total + 1):
        body = cast(
            dict[str, Any],
            owner.get(
                CONTENT_URL.format(
                    attachment_id=attachment.pk, query=f"format=markdown&page={page}"
                )
            ).json(),
        )
        assert _banner_count(body["content"]) == 1
        assert body["content"].startswith(untrusted_banner())


def test_repeated_retrieval_never_double_prefixes(owner: APIClient, task: Any) -> None:
    """The stored description stays un-decorated; delivery prefixes once."""
    attachment = process_ready(task, png_bytes(), name="shot.png", transcript=TRANSCRIPT)
    first = cast(
        dict[str, Any],
        owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=text_ocr")).json(),
    )
    second = cast(
        dict[str, Any],
        owner.get(CONTENT_URL.format(attachment_id=attachment.pk, query="format=text_ocr")).json(),
    )
    assert first == second
    assert _banner_count(second["content"]) == 1
    row = type(attachment).objects.get(pk=attachment.pk)
    assert not row.ocr_text.startswith("[")  # the store holds raw text


def test_image_base64_is_never_prefixed(owner: APIClient, task: Any) -> None:
    attachment = process_ready(task, png_bytes(), name="shot.png")
    response = owner.get(
        CONTENT_URL.format(attachment_id=attachment.pk, query="format=image_base64")
    )
    assert untrusted_banner() not in response.content.decode()
    body = cast(dict[str, Any], response.json())
    assert body["content"] is None and body["description"] is None


# --- the short-metadata exemption (the MT-1.14-04 decision) ------------------


def test_descriptor_short_description_stays_unbannered(owner: APIClient, task: Any) -> None:
    """List/detail descriptor summaries are bounded metadata, not text runs."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    body = cast(dict[str, Any], owner.get(TASK_URL.format(task_id=task.pk)).json())
    embedded = body["attachments"][0]
    assert embedded["short_description"] is not None
    assert not embedded["short_description"].startswith(untrusted_banner())
    detail = owner.get(f"/api/v1/attachments/{attachment.pk}").json()
    assert not detail["short_description"].startswith(untrusted_banner())


def test_error_responses_never_carry_the_banner(owner: APIClient, task: Any) -> None:
    """The envelope is not a text payload (MT-1.14-04 out-of-scope note)."""
    attachment = process_ready(task, MARKDOWN_BYTES, name="notes.md")
    response = owner.get(
        CONTENT_URL.format(attachment_id=attachment.pk, query="format=markdown&page=99")
    )
    assert response.status_code == 400
    assert envelope_code(response) == "VALIDATION_ERROR"
    assert untrusted_banner() not in response.content.decode()
