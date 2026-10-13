"""MT-1.13-01/02 — DescriptionProvider interface, selector, disabled default.

Run with ``pytest backend/tests/attachments/test_description_provider.py -v``.

Proves:

* the interface contract (input, output, typed failure) exists and the
  disabled implementation satisfies it — explicit ``""``, never a
  placeholder caption (MT-1.13-01);
* selection is configuration-driven with **disabled** as the fresh-
  environment default (OQ-07; Section 9.10), unknown names fail fast
  with the supported set, and the programmatic override seam works;
* the disabled provider performs **zero external calls** — network and
  subprocess are blocked for the whole run and the pipeline still
  completes (MT-1.13-02; OQ-07 budget intent);
* the pipeline's caption hook is actually *reached* under the default
  configuration (call-spy on the configured instance — MT-1.13-02 risk
  note: a hook that never fires would make the no-op test vacuous);
* the interface change (attachment identity input) flows through the
  image stage (MT-1.13-01).
"""

from __future__ import annotations

import socket
import subprocess
from typing import Any

import pytest
from django.test import override_settings

from apps.attachments.description import (
    SUPPORTED_DESCRIPTION_PROVIDERS,
    DescriptionProvider,
    DescriptionProviderError,
    DisabledDescriptionProvider,
    get_description_provider,
    set_description_provider,
)
from apps.attachments.ocr import set_ocr_engine
from apps.attachments.pipeline import run_pipeline

from .helpers import StubOcrEngine, make_attachment, make_project, make_task, png_bytes

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    """Uploads and derived artifacts land in an isolated media root."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def clear_provider_override() -> Any:
    """Every test starts and ends on the configuration path."""
    set_description_provider(None)
    yield
    set_description_provider(None)


@pytest.fixture
def task() -> Any:
    return make_task(make_project())


# --- interface contract (MT-1.13-01) ----------------------------------------


def test_disabled_provider_satisfies_the_interface() -> None:
    """Runtime-checkable Protocol: the default answers the contract."""
    provider = DisabledDescriptionProvider()
    assert isinstance(provider, DescriptionProvider)
    assert provider.name == "disabled"


def test_describe_takes_attachment_identity_and_returns_explicit_no_description() -> None:
    """Input contract (identity + image + transcript); output ``""``."""
    caption = DisabledDescriptionProvider().describe(
        attachment_id="3f7a1c9e-5d2b-4f81-9c0a-2e6d8b4f1a70",
        image_png=b"\x89PNG\r\n\x1a\n",
        ocr_text="transcript",
    )
    assert caption == ""  # explicit no-description; never None, never a placeholder


def test_typed_failure_is_the_provider_failure_signal() -> None:
    """Only the typed failure degrades (MT-1.13-05 consumes this flag)."""
    failure = DescriptionProviderError("remote vision provider timed out", transient=True)
    assert failure.reason == "remote vision provider timed out"
    assert failure.transient is True
    assert DescriptionProviderError("malformed", transient=False).transient is False


# --- selection (Section 9.10; OQ-07 default) --------------------------------


def test_fresh_environment_resolves_to_disabled() -> None:
    """No provider settings present → the documented default (9.10)."""
    assert get_description_provider().name == "disabled"
    with override_settings(DESCRIPTION_PROVIDER="disabled"):
        assert isinstance(get_description_provider(), DisabledDescriptionProvider)


def test_override_setting_selects_remote_by_name() -> None:
    """Overriding the setting selects the remote implementation by name.

    Constructed with explicit test values: selection and construction
    are separate concerns (the settings fail-fast is MT-1.13-03's test).
    """
    from apps.attachments.description_remote import RemoteVisionDescriptionProvider

    set_description_provider(None)
    with (
        override_settings(
            DESCRIPTION_PROVIDER="anthropic-vision",
            DESCRIPTION_REMOTE_BASE_URL="http://vision.invalid",
            DESCRIPTION_REMOTE_MODEL="vision-model",
            DESCRIPTION_REMOTE_API_KEY="test-key",  # pragma: allowlist secret
        ),
    ):
        provider = get_description_provider()
    assert isinstance(provider, RemoteVisionDescriptionProvider)


def test_unknown_provider_name_fails_fast_with_the_supported_set() -> None:
    """Section 9.10: an unknown name never silently degrades."""
    from django.core.exceptions import ImproperlyConfigured

    with override_settings(DESCRIPTION_PROVIDER="gemini-vision"):
        with pytest.raises(ImproperlyConfigured) as caught:
            get_description_provider()
    message = str(caught.value)
    assert "gemini-vision" in message
    assert sorted(SUPPORTED_DESCRIPTION_PROVIDERS) == ["anthropic-vision", "disabled"]
    for name in SUPPORTED_DESCRIPTION_PROVIDERS:
        assert name in message


def test_programmatic_override_seam() -> None:
    """The test seam installs and clears a provider instance."""
    spy = DisabledDescriptionProvider()
    set_description_provider(spy)
    assert get_description_provider() is spy
    set_description_provider(None)
    assert get_description_provider() is not spy


# --- disabled: zero external calls, OCR-only completion (MT-1.13-02) --------


@pytest.fixture
def network_and_subprocess_blocked(monkeypatch: Any) -> None:
    """Fail the test if any socket or subprocess call happens."""

    def _no_socket(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the disabled provider must open no socket")

    def _no_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the disabled provider must spawn no subprocess")

    monkeypatch.setattr(socket, "socket", _no_socket)
    monkeypatch.setattr(subprocess, "run", _no_run)
    monkeypatch.setattr(subprocess, "Popen", _no_run)


def test_default_pipeline_completes_ocr_only_with_no_external_calls(
    task: Any, network_and_subprocess_blocked: None
) -> None:
    """WP-1.13 first acceptance half: default settings → OCR-only ``ready``.

    The call-spy proves the hook ran (the configured default instance's
    ``describe`` was invoked) — otherwise this test would pass vacuously
    (MT-1.13-02 risk note). The OCR stub is installed *before* the
    network block so the stage's own work is unaffected.
    """
    calls: list[str] = []
    original = DisabledDescriptionProvider.describe

    def spy(self: Any, **kwargs: Any) -> str:
        calls.append(kwargs["attachment_id"])
        return original(self, **kwargs)

    set_ocr_engine(StubOcrEngine("engine output"))
    DisabledDescriptionProvider.describe = spy  # type: ignore[method-assign]
    try:
        attachment = make_attachment(task, png_bytes(), name="shot.png")
        assert run_pipeline(str(attachment.pk)) == "ready"
    finally:
        DisabledDescriptionProvider.describe = original  # type: ignore[method-assign]
        set_ocr_engine(None)

    row = type(attachment).objects.get(pk=attachment.pk)
    assert row.ocr_text == "engine output"  # OCR-only is a complete state
    assert row.layout_caption == ""  # no description persisted
    assert row.failure_detail == ""  # the no-op caption step recorded no failure
    assert calls == [str(attachment.pk)]  # the caption hook was reached


def test_disabled_provider_is_the_pipeline_default(task: Any) -> None:
    """With no override and default settings the disabled provider runs."""
    set_ocr_engine(StubOcrEngine())
    attachment = make_attachment(task, png_bytes(), name="shot.png")
    try:
        assert run_pipeline(str(attachment.pk)) == "ready"
        row = type(attachment).objects.get(pk=attachment.pk)
        assert row.layout_caption == ""
    finally:
        set_ocr_engine(None)
