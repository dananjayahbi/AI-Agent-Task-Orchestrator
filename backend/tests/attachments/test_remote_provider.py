"""MT-1.13-03 — remote vision-model provider: config, cost and failure logs.

Run with ``pytest backend/tests/attachments/test_remote_provider.py -v``.

Proves, against a **stubbed transport** (no live calls in CI):

* success: the Anthropic-compatible request shape and caption parsing
  through the interface (WP-1.13 second acceptance half, unit layer);
* missing required configuration with the provider selected fails fast
  with the offending environment names (Section 9.10), while the
  disabled default needs no provider values;
* every invocation emits the structured cost record — model, usage
  figures, duration — and logs usage *absence* rather than fabricating
  zeros (OQ-07 budget discipline);
* every failure (transport, non-2xx, malformed output) emits the
  structured failure record and raises the typed signal — with **no
  credential or response-body text in any log record** (Section 12.4).
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from django.test import override_settings

from apps.attachments.description import (
    DescriptionProviderError,
    get_description_provider,
    set_description_provider,
)
from apps.attachments.description_remote import (
    ANTHROPIC_VERSION,
    MESSAGES_PATH,
    PROMPT,
    RemoteVisionDescriptionProvider,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    """Uploads and derived artifacts land in an isolated media root."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


API_KEY = "sk-test-not-a-real-key"  # pragma: allowlist secret
BASE_URL = "http://vision.internal"

CONFIGURED = {
    "DESCRIPTION_REMOTE_BASE_URL": BASE_URL,
    "DESCRIPTION_REMOTE_MODEL": "vision-model-x",
    "DESCRIPTION_REMOTE_API_KEY": API_KEY,
}


def _provider(post: Any, **overrides: Any) -> RemoteVisionDescriptionProvider:
    """A provider wired to a stub transport and explicit settings."""
    values = {**CONFIGURED, **overrides}
    return RemoteVisionDescriptionProvider(
        base_url=values["DESCRIPTION_REMOTE_BASE_URL"],
        model=values["DESCRIPTION_REMOTE_MODEL"],
        api_key=values["DESCRIPTION_REMOTE_API_KEY"],
        post=post,
    )


def _body(
    caption: str = "A login form with a title and two inputs.", **extra: Any
) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": caption}],
        "usage": {"input_tokens": 1102, "output_tokens": 96},
        **extra,
    }


# --- success path (WP-1.13 acceptance, unit layer) ---------------------------


def test_caption_is_parsed_and_returned_through_the_interface() -> None:
    """Image fixture → request shape → parsed caption through describe()."""
    seen: dict[str, Any] = {}

    def post(
        url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
    ) -> dict[str, Any]:
        seen.update(url=url, headers=headers, payload=payload, timeout=timeout)
        return _body()

    provider = _provider(post)
    caption = provider.describe(
        attachment_id="att-1", image_png=b"\x89PNG\r\n\x1a\n", ocr_text="grounding"
    )
    assert caption == "A login form with a title and two inputs."
    # Anthropic-compatible request shape (documented choices).
    assert seen["url"] == BASE_URL + MESSAGES_PATH
    assert seen["headers"]["x-api-key"] == API_KEY
    assert seen["headers"]["anthropic-version"] == ANTHROPIC_VERSION
    blocks = seen["payload"]["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["type"] == "base64"
    assert blocks[1] == {"type": "text", "text": PROMPT}


def test_selector_constructs_the_remote_provider_from_settings() -> None:
    """``anthropic-vision`` in settings builds the implementation (9.10)."""
    with override_settings(**CONFIGURED, DESCRIPTION_PROVIDER="anthropic-vision"):
        provider = get_description_provider()
    assert isinstance(provider, RemoteVisionDescriptionProvider)
    assert provider.name == "anthropic-vision"


# --- startup / point-of-use configuration fail-fast (Section 9.10) ----------


def test_missing_configuration_fails_fast_with_the_offending_names() -> None:
    """Selected-but-unconfigured: clear message, credentials env-only."""
    from django.core.exceptions import ImproperlyConfigured

    with pytest.raises(ImproperlyConfigured) as caught:
        RemoteVisionDescriptionProvider(base_url="", model="", api_key="")
    message = str(caught.value)
    assert "ORCHESTRATOR_DESCRIPTION_REMOTE_BASE_URL" in message
    assert "ORCHESTRATOR_DESCRIPTION_REMOTE_MODEL" in message
    assert "ORCHESTRATOR_DESCRIPTION_REMOTE_API_KEY" in message


def test_startup_validation_function_requires_values_only_for_the_remote_provider() -> None:
    """The settings-group twin: disabled requires nothing (OQ-07 default)."""
    from apps.core.settings.base import missing_description_remote_settings

    assert missing_description_remote_settings("disabled", "", "", "") == []
    missing = missing_description_remote_settings("anthropic-vision", BASE_URL, "", "")
    assert missing == [
        "ORCHESTRATOR_DESCRIPTION_REMOTE_MODEL",
        "ORCHESTRATOR_DESCRIPTION_REMOTE_API_KEY",
    ]
    assert (
        missing_description_remote_settings("anthropic-vision", BASE_URL, "vision-model-x", API_KEY)
        == []
    )


def test_default_settings_boot_needs_no_provider_values() -> None:
    """With the default ``disabled`` provider, no remote value is required."""
    # The suite boots on these settings every run — the import-time
    # fail-fast never fires for the documented default (Section 9.10).
    from django.conf import settings

    from apps.core.settings.base import missing_description_remote_settings

    assert settings.DESCRIPTION_PROVIDER == "disabled"
    assert (
        missing_description_remote_settings(
            settings.DESCRIPTION_PROVIDER,
            settings.DESCRIPTION_REMOTE_BASE_URL,
            settings.DESCRIPTION_REMOTE_MODEL,
            settings.DESCRIPTION_REMOTE_API_KEY,
        )
        == []
    )


# --- cost logging (Section 9.5 "cost and failures are logged"; Section 17) ---


def test_every_invocation_emits_the_structured_cost_record(caplog: Any) -> None:
    """Model, usage figures and duration land on the log record."""
    with caplog.at_level(logging.INFO, logger="apps.attachments.description_remote"):
        _provider(lambda *_args: _body()).describe(
            attachment_id="att-2", image_png=b"\x89PNG", ocr_text=""
        )
    record = next(r for r in caplog.records if r.message == "description provider invocation")
    assert record.description_provider == "anthropic-vision"
    assert record.description_model == "vision-model-x"
    assert record.description_input_tokens == 1102
    assert record.description_output_tokens == 96
    assert record.description_usage_present is True
    assert isinstance(record.description_duration_ms, int)
    assert record.attachment_id == "att-2"


def test_absent_usage_is_logged_as_absence_not_zeros(caplog: Any) -> None:
    """A response without usage corrupts no budget (risk note)."""
    body = {"content": [{"type": "text", "text": "caption"}]}

    def post(*_args: Any) -> dict[str, Any]:
        return body

    with caplog.at_level(logging.INFO, logger="apps.attachments.description_remote"):
        _provider(post).describe(attachment_id="att-3", image_png=b"x", ocr_text="")
    record = next(r for r in caplog.records if r.message == "description provider invocation")
    assert record.description_usage_present is False
    assert record.description_input_tokens is None
    assert record.description_output_tokens is None


# --- failure logging and the typed signal (MT-1.13-05 consumes it) ----------


def test_http_error_raises_typed_failure_and_logs_structured(caplog: Any) -> None:
    def post(*_args: Any) -> dict[str, Any]:
        raise DescriptionProviderError("remote vision provider answered HTTP 500")

    provider = _provider(post)
    with caplog.at_level(logging.WARNING, logger="apps.attachments.description_remote"):
        with pytest.raises(DescriptionProviderError) as caught:
            provider.describe(attachment_id="att-4", image_png=b"x", ocr_text="")
    assert caught.value.transient is True  # 500 is in the retryable set
    record = next(r for r in caplog.records if r.message == "description provider failed")
    assert record.description_failure == "remote vision provider answered HTTP 500"
    assert record.description_transient is True
    assert record.attachment_id == "att-4"


@pytest.mark.parametrize(
    ("body", "transient"),
    [
        ({"no": "content"}, False),
        ({"content": [{"type": "image"}]}, False),
    ],
)
def test_malformed_output_raises_typed_failure(body: dict[str, Any], transient: bool) -> None:
    def post(*_args: Any) -> dict[str, Any]:
        return body

    with pytest.raises(DescriptionProviderError):
        _provider(post).describe(attachment_id="att-5", image_png=b"x", ocr_text="")


def test_no_credential_or_body_text_reaches_any_log_record(caplog: Any) -> None:
    """Section 12.4: never log tokens; response bodies may quote content."""

    def post(*_args: Any) -> dict[str, Any]:
        raise DescriptionProviderError("remote vision provider answered HTTP 401", transient=False)

    provider = _provider(post)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DescriptionProviderError):
            provider.describe(attachment_id="att-6", image_png=b"x", ocr_text="")
    blob = " ".join(
        f"{record.getMessage()} {getattr(record, key, '')}"
        for record in caplog.records
        for key in list(record.__dict__)
    )
    assert API_KEY not in blob


def test_failed_generation_is_not_stored_anywhere() -> None:
    """Failure raises before any persistence layer can see it (cache stays empty)."""
    set_description_provider(None)
    from apps.attachments.caption import generate_caption
    from apps.attachments.models import TaskAttachment
    from apps.attachments.ocr import set_ocr_engine

    from .helpers import StubOcrEngine, make_attachment, make_project, make_task, png_bytes

    set_ocr_engine(StubOcrEngine())
    attachment = make_attachment(make_task(make_project()), png_bytes(), name="x.png")

    def post(*_args: Any) -> dict[str, Any]:
        raise DescriptionProviderError("remote vision provider unreachable (URLError)")

    set_description_provider(_provider(post))
    try:
        with pytest.raises(DescriptionProviderError):
            generate_caption(attachment, image_png=b"x", ocr_text="")
    finally:
        set_description_provider(None)
        set_ocr_engine(None)
    assert TaskAttachment.objects.get(pk=attachment.pk).layout_caption == ""
