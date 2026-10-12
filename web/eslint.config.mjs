import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import prettier from 'eslint-config-prettier/flat';

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  prettier,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    '.next/**',
    'out/**',
    'build/**',
    'next-env.d.ts',
    // Generated API client (MT-4.1-03): machine-owned output from
    // schemas/openapi.yaml — linting it locally would fight the drift gate
    // (the import-boundary test in tests/api/ guards how it is consumed).
    'lib/api/generated/**',
  ]),
]);

export default eslintConfig;
