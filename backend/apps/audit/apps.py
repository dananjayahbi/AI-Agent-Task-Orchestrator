"""App registration for the ``audit`` module (parent plan Section 9.1)."""

from __future__ import annotations

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Audit reports, Policy Engine, review decisions (Section 9.1)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"

    def ready(self) -> None:
        """Install the Policy Engine on both decision seams (MT-3.4-07).

        The events app's precedent for *hook* installation: one
        registration, one code path — invariant 8.3.4 ("only the Policy
        Engine can set a policy-approved outcome") holds from process
        start via :func:`ensure_policy_engine_wired`. Registry rows
        stay lazily wired (the WP-1.5 suites' snapshot/restore owns
        that state). Test fixtures may still replace or remove the
        hooks explicitly; removing them restores the documented
        fail-closed escalate defaults (MT-3.2-05 / MT-3.3-05).
        """
        from .policy.wiring import ensure_policy_engine_wired

        ensure_policy_engine_wired()
