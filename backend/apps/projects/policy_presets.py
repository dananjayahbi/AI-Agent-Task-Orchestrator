"""Framework preset library for the three Section 7.2 policy glob fields.

Data, not code branches (WP-3.1 hard rule): a versioned, read-only
registry whose entries supply ``critical_path_globs``,
``migration_path_globs`` and ``sensitive_config_globs`` for one
framework. Selection happens through the API's ``policy_preset`` input
(``POST /projects`` and ``PATCH /projects/{pid}/policy``) — the
serializer expands a preset id into the three glob fields; nothing here
branches on framework behavior.

Each preset's globs are derived from the Section 7.2 category meanings
(CI/CD + root migrations + security config → critical; framework
migration directories → migration; env files + key material + security
rules → sensitive) with the derivation recorded next to the data so a
reviewer can audit it (MT-3.1-02 risk note — the plan stays
authoritative; these are documented, owner-confirmable choices, Section
20.1 item 5). Every glob is repo-root-relative and passes
:func:`apps.projects.services.globs.validate_glob_list` — a test locks
that invariant, so editing a preset without re-validating fails CI.

Versioning: ``PRESET_LIBRARY_VERSION`` bumps whenever any preset's glob
content changes; preset *ids* are stable API values and are never
renamed or dropped (clients select them by id).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .services.globs import validate_glob_list

PRESET_LIBRARY_VERSION: Final[int] = 1


@dataclass(frozen=True)
class PolicyPreset:
    """One framework's glob triple plus its display metadata."""

    id: str
    title: str
    description: str
    critical_path_globs: tuple[str, ...]
    migration_path_globs: tuple[str, ...]
    sensitive_config_globs: tuple[str, ...]


DJANGO: Final[PolicyPreset] = PolicyPreset(
    id="django",
    title="Django",
    description=(
        "CI/CD workflows and root migrations, Django settings/security "
        "modules as critical; per-app migrations directories as migration; "
        "env files, key material and local settings as sensitive."
    ),
    # Critical = CI/CD + root migrations + security config (7.2): the CI
    # trio, a top-level migrations/ directory, security modules and the
    # settings tree (SECRET_KEY/DEBUG/security middleware live there).
    critical_path_globs=(
        ".github/workflows/*",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "migrations/*",
        "**/security*.py",
        "**/settings*.py",
        "**/settings/*.py",
    ),
    # Migration = framework-specific (7.2): Django writes schema changes
    # as per-app migrations packages.
    migration_path_globs=(
        "**/migrations/*.py",
        "migrations/*",
    ),
    # Sensitive = env files, key material, security rules (7.2): env
    # variants, PEM/key files, credential/secret filenames, and the
    # local-setting modules that typically carry production secrets.
    sensitive_config_globs=(
        ".env*",
        "**/*.env",
        "**/*.pem",
        "**/*.key",
        "**/*credentials*",
        "**/*secrets*",
        "**/local_settings.py",
        "**/settings/local.py",
    ),
)

NEXTJS: Final[PolicyPreset] = PolicyPreset(
    id="nextjs",
    title="Next.js",
    description=(
        "CI/CD workflows, next.config and middleware (auth boundary) as "
        "critical; Prisma/Drizzle migration directories as migration; env "
        "files and key material as sensitive."
    ),
    # Critical = CI/CD + security config (7.2): the CI trio plus
    # next.config (build/deploy surface) and middleware (the auth/security
    # boundary in a Next.js app).
    critical_path_globs=(
        ".github/workflows/*",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "next.config.*",
        "middleware.ts",
        "middleware.js",
        "middleware.tsx",
    ),
    # Migration = framework-specific (7.2): Prisma and Drizzle are the
    # dominant migration producers in the Next.js ecosystem.
    migration_path_globs=(
        "prisma/migrations/*",
        "drizzle/*",
    ),
    # Sensitive = env files, key material (7.2): Next.js keeps runtime
    # configuration in .env* files by convention.
    sensitive_config_globs=(
        ".env*",
        "**/*.env",
        "**/*.pem",
        "**/*.key",
        "**/*credentials*",
        "**/*secrets*",
    ),
)

FLUTTER: Final[PolicyPreset] = PolicyPreset(
    id="flutter",
    title="Flutter",
    description=(
        "CI/CD workflows plus Android signing configuration as critical; "
        "Dart/SQL migration directories as migration; keystores, "
        "google-services and env material as sensitive."
    ),
    # Critical = CI/CD + security config (7.2): the CI trio, Codemagic
    # (Flutter CI), and the Android signing configuration (build.gradle /
    # key.properties control the release signing identity).
    critical_path_globs=(
        ".github/workflows/*",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "codemagic.yaml",
        "android/app/build.gradle",
        "android/app/build.gradle.kts",
        "android/key.properties",
    ),
    # Migration = framework-specific (7.2): Flutter apps migrate local
    # databases (drift/sqflite) via Dart migration units or SQL schemas.
    migration_path_globs=(
        "lib/**/migrations/*.dart",
        "**/drift/**",
        "**/migrations/*.sql",
    ),
    # Sensitive = env files, key material, security rules (7.2): Android
    # keystores, Apple/Google service config (API keys baked in), PEM/key
    # material and secret-named files.
    sensitive_config_globs=(
        ".env*",
        "**/*.env",
        "**/*.pem",
        "**/*.key",
        "**/*.jks",
        "**/*.keystore",
        "android/key.properties",
        "**/google-services.json",
        "**/GoogleService-Info.plist",
        "**/*credentials*",
        "**/*secrets*",
    ),
)

PRESETS: Final[dict[str, PolicyPreset]] = {
    DJANGO.id: DJANGO,
    NEXTJS.id: NEXTJS,
    FLUTTER.id: FLUTTER,
}

PRESET_IDS: Final[tuple[str, ...]] = tuple(PRESETS)


def list_presets() -> list[PolicyPreset]:
    """Every preset, stable order — the library as a plain DTO list."""
    return list(PRESETS.values())


def get_preset(preset_id: str) -> PolicyPreset:
    """Resolve a preset id; unknown ids raise a catalog ``ValidationError``.

    The ChoiceField on the serializers rejects unknown ids at the boundary
    already; this lookup re-checks so direct service callers (bridge,
    future WP-4.x surfaces) get the same catalog answer, never a KeyError.
    """
    from rest_framework.exceptions import ValidationError

    preset = PRESETS.get(preset_id)
    if preset is None:
        raise ValidationError(
            {
                "policy_preset": [
                    f"Unknown preset id {preset_id!r}; valid ids: {', '.join(PRESET_IDS)}."
                ]
            }
        )
    return preset


def preset_glob_fields(preset: PolicyPreset) -> dict[str, list[str]]:
    """The preset's three glob lists as fresh, validated copies.

    Validation runs here (not only in tests) so preset data that drifts
    from the Section 12.3 rules is refused at write time with the catalog
    ``VALIDATION_ERROR`` instead of persisting a broken glob — the
    regression guard MT-3.1-02's AC asks for, enforced at runtime too.
    Fresh lists per call: JSONField rows never share one list object.
    """
    return {
        "critical_path_globs": validate_glob_list(
            preset.critical_path_globs, field="critical_path_globs"
        ),
        "migration_path_globs": validate_glob_list(
            preset.migration_path_globs, field="migration_path_globs"
        ),
        "sensitive_config_globs": validate_glob_list(
            preset.sensitive_config_globs, field="sensitive_config_globs"
        ),
    }


__all__ = [
    "PRESETS",
    "PRESET_IDS",
    "PRESET_LIBRARY_VERSION",
    "PolicyPreset",
    "get_preset",
    "list_presets",
    "preset_glob_fields",
]
