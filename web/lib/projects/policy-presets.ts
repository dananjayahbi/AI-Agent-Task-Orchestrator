/**
 * Client transcription of WP-3.1's policy preset library (MT-4.10-03;
 * Section 19 WP-3.1 — the "presets selectable" acceptance implies the
 * library is reusable here).
 *
 * **Drift discipline:** the tuples are copied verbatim from
 * `backend/apps/projects/policy_presets.py` and pinned by
 * `web/tests/projects/policy-presets.test.ts`, which parses that source
 * and asserts set equality — a backend preset edit without a matching
 * client edit fails CI. The UI uses this transcription to POPULATE the
 * three glob textareas after explicit confirmation (the MT's flow: the
 * Owner sees and can hand-edit the exact globs before saving), rather
 * than sending the server's `policy_preset` shortcut — which cannot be
 * combined with manual glob edits in one request (serializer rule:
 * `policy_preset` + explicit globs = VALIDATION_ERROR). The shortcut
 * remains available to API callers; the form prefers visible, editable
 * values.
 */
export type PolicyPresetId = 'django' | 'nextjs' | 'flutter';

export type PolicyPreset = {
  id: PolicyPresetId;
  title: string;
  description: string;
  critical_path_globs: string[];
  migration_path_globs: string[];
  sensitive_config_globs: string[];
};

/** Matches the backend constant — pinned by the drift test. */
export const PRESET_LIBRARY_VERSION = 1;

export const POLICY_PRESETS: Record<PolicyPresetId, PolicyPreset> = {
  django: {
    id: 'django',
    title: 'Django',
    description:
      'CI/CD workflows and root migrations, Django settings/security modules as critical; per-app migrations directories as migration; env files, key material and local settings as sensitive.',
    critical_path_globs: [
      '.github/workflows/*',
      '.gitlab-ci.yml',
      'Jenkinsfile',
      'migrations/*',
      '**/security*.py',
      '**/settings*.py',
      '**/settings/*.py',
    ],
    migration_path_globs: ['**/migrations/*.py', 'migrations/*'],
    sensitive_config_globs: [
      '.env*',
      '**/*.env',
      '**/*.pem',
      '**/*.key',
      '**/*credentials*',
      '**/*secrets*',
      '**/local_settings.py',
      '**/settings/local.py',
    ],
  },
  nextjs: {
    id: 'nextjs',
    title: 'Next.js',
    description:
      'CI/CD workflows, next.config and middleware (auth boundary) as critical; Prisma/Drizzle migration directories as migration; env files and key material as sensitive.',
    critical_path_globs: [
      '.github/workflows/*',
      '.gitlab-ci.yml',
      'Jenkinsfile',
      'next.config.*',
      'middleware.ts',
      'middleware.js',
      'middleware.tsx',
    ],
    migration_path_globs: ['prisma/migrations/*', 'drizzle/*'],
    sensitive_config_globs: [
      '.env*',
      '**/*.env',
      '**/*.pem',
      '**/*.key',
      '**/*credentials*',
      '**/*secrets*',
    ],
  },
  flutter: {
    id: 'flutter',
    title: 'Flutter',
    description:
      'CI/CD workflows plus Android signing configuration as critical; Dart/SQL migration directories as migration; keystores, google-services and env material as sensitive.',
    critical_path_globs: [
      '.github/workflows/*',
      '.gitlab-ci.yml',
      'Jenkinsfile',
      'codemagic.yaml',
      'android/app/build.gradle',
      'android/app/build.gradle.kts',
      'android/key.properties',
    ],
    migration_path_globs: ['lib/**/migrations/*.dart', '**/drift/**', '**/migrations/*.sql'],
    sensitive_config_globs: [
      '.env*',
      '**/*.env',
      '**/*.pem',
      '**/*.key',
      '**/*.jks',
      '**/*.keystore',
      'android/key.properties',
      '**/google-services.json',
      '**/GoogleService-Info.plist',
      '**/*credentials*',
      '**/*secrets*',
    ],
  },
};

export const POLICY_PRESET_IDS: PolicyPresetId[] = ['django', 'nextjs', 'flutter'];
