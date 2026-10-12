"""MT-2.3-04 — error translation: catalog-guarded code + hint + next action.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.3-api-client/
MT-2.3-04-error-translation.md (parent plan Sections 9.2, 10.5, 20.4 item 5,
20.5; NFR-04, NFR-12).
"""

from __future__ import annotations

import pytest

from orchestrator_bridge.api_errors import (
    CANONICAL_ERROR_CODES,
    ApiError,
    ErrorCode,
    ErrorKind,
)
from orchestrator_bridge.error_translation import HINTS, translate_error


def _error(
    code: ErrorCode | str = ErrorCode.SERVER_ERROR,
    *,
    retryable: bool = False,
    message: str = "backend said something",
    details: dict[str, object] | None = None,
    correlation_id: str | None = "c0a8-4f2e-91d7",
) -> ApiError:
    return ApiError(
        code=code,  # type: ignore[arg-type]  # str input is the out-of-catalog case
        message=message,
        retryable=retryable,
        kind=ErrorKind.ENVELOPE,
        details=details,
        correlation_id=correlation_id,
        status_code=500,
    )


# --- AC 1: every entry keys on a catalog code --------------------------------


def test_every_hint_key_is_a_catalog_code() -> None:
    """Section 20.4 item 5: no out-of-catalog key may exist in the table."""
    assert set(HINTS) <= set(CANONICAL_ERROR_CODES)
    assert len(CANONICAL_ERROR_CODES) == 19  # error-envelope.md published count


def test_every_catalog_code_has_non_empty_guidance() -> None:
    for code in CANONICAL_ERROR_CODES:
        hint, next_action = HINTS[code]
        assert hint.strip(), f"{code} hint is empty"
        assert next_action.strip(), f"{code} next_action is empty"


def test_translate_rejects_out_of_catalog_code() -> None:
    with pytest.raises(ValueError, match="NOT_A_REAL_CODE"):
        translate_error(_error("NOT_A_REAL_CODE"))


# --- AC 2/3: all three parts plus correlation id, passthrough verbatim -------


def test_translated_error_carries_code_hint_next_action_and_correlation() -> None:
    translated = translate_error(
        _error(
            ErrorCode.TASK_ALREADY_CLAIMED,
            message="Task PID00007-T004 is held by another worker.",
            details={"task_id": "PID00007-T004", "state": "in_progress"},
        )
    )
    assert translated.code is ErrorCode.TASK_ALREADY_CLAIMED
    assert translated.hint
    assert translated.next_action
    assert translated.correlation_id == "c0a8-4f2e-91d7"


def test_passthrough_preserves_message_details_correlation_and_retryable() -> None:
    """Section 20.5: nothing beyond hint/next-action is added or rewritten."""
    original = _error(
        ErrorCode.LEASE_EXPIRED,
        retryable=True,
        message="Lease expired at 12:00Z.",
        details={"task_id": "PID00007-T004", "lease_generation": 7},
        correlation_id="feed-5eed-0001",
    )
    translated = translate_error(original)
    assert translated.message == original.message
    assert translated.details == original.details
    assert translated.correlation_id == original.correlation_id
    assert translated.retryable is original.retryable


@pytest.mark.parametrize(
    ("code", "retryable"),
    [
        (ErrorCode.SERVER_ERROR, True),
        (ErrorCode.RATE_LIMITED, True),
        (ErrorCode.TASK_ALREADY_CLAIMED, False),
    ],
)
def test_retryable_classification_survives_translation(code: ErrorCode, retryable: bool) -> None:
    assert translate_error(_error(code, retryable=retryable)).retryable is retryable


# --- AC 5: representative code classes ---------------------------------------


def test_claim_code_suggests_relisting() -> None:
    translated = translate_error(_error(ErrorCode.TASK_ALREADY_CLAIMED))
    assert "get_available_tasks" in translated.next_action


def test_lease_expired_carries_the_risk02_stop_and_reclaim_path() -> None:
    translated = translate_error(_error(ErrorCode.LEASE_EXPIRED))
    assert "claim_task" in translated.next_action
    assert "Stop" in translated.next_action
    assert "checkpoint" in translated.next_action.lower()


def test_auth_code_points_at_token_configuration() -> None:
    translated = translate_error(_error(ErrorCode.AUTH_REQUIRED, retryable=False))
    assert "token" in (translated.hint + translated.next_action).lower()
    assert "orchestrator init" in translated.next_action


def test_concurrency_code_suggests_release_or_wait() -> None:
    translated = translate_error(_error(ErrorCode.CONCURRENCY_LIMIT_REACHED))
    assert "release_task" in translated.next_action or "wait" in translated.next_action


def test_server_and_rate_codes_stay_retryable_and_actionable() -> None:
    for code in (ErrorCode.SERVER_ERROR, ErrorCode.RATE_LIMITED):
        translated = translate_error(_error(code, retryable=True))
        assert translated.retryable is True
        assert "retry" in translated.next_action.lower()


def test_default_branch_names_the_canonical_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """A catalog code without wording still yields actionable, code-named guidance."""
    monkeypatch.delitem(HINTS, ErrorCode.SERVER_ERROR)
    translated = translate_error(
        _error(ErrorCode.SERVER_ERROR, retryable=True, correlation_id="aaaa-bbbb-cccc")
    )
    assert translated.code is ErrorCode.SERVER_ERROR
    assert ErrorCode.SERVER_ERROR.value in translated.hint
    assert translated.next_action.strip()
    assert "aaaa-bbbb-cccc" in translated.next_action
    assert translated.retryable is True  # default branch changes no classification


def test_translated_code_serializes_to_the_wire_value() -> None:
    """StrEnum: tool handlers emit the canonical wire string, not 'ErrorCode.X'."""
    translated = translate_error(_error(ErrorCode.VALIDATION_ERROR))
    assert str(translated.code) == "VALIDATION_ERROR"
    assert translated.code.value == "VALIDATION_ERROR"
