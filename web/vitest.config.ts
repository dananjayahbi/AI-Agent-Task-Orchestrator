import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

/**
 * Vitest runner for the web package (MT-4.1-02 / MT-4.1-04 test suites;
 * runner choice recorded in the WP changelog per Section 20.4 item 1).
 * CI discovers test files under web/ (excluding node_modules and .next) and
 * runs `npm --prefix web run test`.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('.', import.meta.url)) },
  },
  test: {
    // Globals let @testing-library/react self-register afterEach cleanup
    // between tests (without it, renders accumulate across cases).
    globals: true,
    include: ['tests/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://localhost:3000' } },
  },
});
