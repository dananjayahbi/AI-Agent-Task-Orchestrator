/**
 * Shared API test harness (MT-4.2-01): routes mocked `fetch` requests the
 * way the backend would answer — through the real generated client, so every
 * component test also proves NFR-11 (no test-only call paths).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { vi, type Mock } from 'vitest';

export function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Section 9.2 envelope (nested) with catalog code + safe default message. */
export function errorResponse(
  code: string,
  status: number,
  message = `${code} from the test server.`,
): Response {
  return jsonResponse(
    {
      error: {
        code,
        message,
        retryable: status >= 500,
        details: null,
        correlation_id: 'corr-test',
      },
    },
    status,
  );
}

export type RecordedCall = {
  method: string;
  pathname: string;
  search: string;
  body: unknown;
};

type RouteInfo = RecordedCall & { request: Request };

export type Route = {
  method: string;
  /** Tested against `pathname + search`. */
  match: RegExp;
  respond: (info: RouteInfo) => Response | Promise<Response>;
};

/**
 * Install a router-style fetch mock; returns every recorded call so tests
 * can assert request shape (cursor paging, bodies, headers).
 */
export function installApi(routes: Route[]): { calls: RecordedCall[]; fetchMock: Mock } {
  const calls: RecordedCall[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url);
    let body: unknown;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try {
        body = await request.clone().json();
      } catch {
        body = undefined;
      }
    }
    const info: RouteInfo = {
      method: request.method,
      pathname: url.pathname,
      search: url.search,
      body,
      request,
    };
    calls.push(info);
    const route = routes.find(
      (candidate) =>
        candidate.method === request.method &&
        candidate.match.test(`${info.pathname}${info.search}`),
    );
    if (route === undefined) {
      console.error(`installApi: unmocked ${request.method} ${info.pathname}${info.search}`);
      throw new Error(`unmocked ${request.method} ${info.pathname}${info.search}`);
    }
    return route.respond(info);
  });
  vi.stubGlobal('fetch', fetchMock);
  return { calls, fetchMock };
}

/** Minimal sample project matching the generated `Project` contract. */
export function makeProject(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'PID00001',
    name: 'Tea Factory ERP',
    repo_path: '/srv/repos/tea-erp',
    active_status: 'active',
    default_branch: 'main',
    system_prompt_rules: '',
    agent_policy: 1,
    task_counter: 0,
    created_at: '2026-10-01T09:00:00Z',
    updated_at: '2026-10-01T09:00:00Z',
    ...overrides,
  };
}

export function pageOf(results: unknown[], nextCursor: string | null = null) {
  return { results, next_cursor: nextCursor };
}

/** Complete ProjectPolicy fixture (all contract-required fields). */
export function makePolicy(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    lease_duration_minutes: 45,
    lease_max_total_minutes: 240,
    lease_extension_mode: 'checkpoint_only',
    max_retries: 3,
    max_concurrent_tasks: 1,
    autonomous_diff_threshold_lines: 250,
    auditor_min_confidence: 4,
    critical_path_globs: ['.github/**'],
    migration_path_globs: ['**/migrations/**'],
    sensitive_config_globs: ['.env*'],
    auto_complete_enabled: true,
    merge_strategy: 'squash',
    branch_prefix: 'feat/{PID}-',
    audit_required_default: true,
    stalled_after_minutes: 20,
    ...overrides,
  };
}

/** Render a client component inside a fresh non-retrying query cache. */
export function renderWithQueryClient(
  ui: ReactElement,
  options: { queryClient?: QueryClient } = {},
): RenderResult & { queryClient: QueryClient } {
  const queryClient =
    options.queryClient ??
    new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  const view = render(ui, { wrapper: Wrapper });
  return { ...view, queryClient };
}
