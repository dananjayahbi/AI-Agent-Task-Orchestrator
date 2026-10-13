/**
 * Shared API test harness (MT-4.2-01): routes mocked `fetch` requests the
 * way the backend would answer — through the real generated client, so every
 * component test also proves NFR-11 (no test-only call paths).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { vi, type Mock } from 'vitest';

import type { Task } from '@/lib/api/generated/types.gen';

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

/** Complete Task fixture matching the generated `Task` contract (WP-4.3). */
export function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'PID00001-T001',
    project_id: 'PID00001',
    title: 'Implement login form',
    description: '',
    acceptance_criteria: [],
    target_scope: [],
    test_command: '',
    priority: 'medium',
    state: 'pending',
    version: 1,
    worker_agent_id: null,
    worker_session_id: null,
    claimed_role: null,
    lease_acquired_at: null,
    lease_expires_at: null,
    last_checkpoint_at: null,
    failure_retry_count: 0,
    attempt_number: 0,
    audit_required: true,
    review_reason: null,
    latest_feedback: '',
    merge_status: 'none',
    archived_at: null,
    created_by: null,
    created_at: '2026-10-01T09:00:00Z',
    updated_at: '2026-10-01T09:00:00Z',
    depends_on: [],
    ...overrides,
  };
}

/** Section 9.6 event envelope fixture (WP-4.3 stream tests). */
export function makeEventEnvelope(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    type: 'task.transitioned',
    project_id: 'PID00001',
    task_id: 'PID00001-T001',
    occurred_at: '2026-10-01T10:00:00Z',
    actor: { type: 'system', ref: 'lease-sweeper' },
    data: {},
    ...overrides,
  };
}

export type SseConnection = {
  response: Response;
  /** One `id:` + `data:` frame (Section 9.6 wire shape, MT-1.10-01). */
  frame: (id: number, envelope: unknown) => void;
  /** `: heartbeat` comment line (MT-1.10-04) — carries no id or data. */
  heartbeat: () => void;
  /** Clean stream end — the hook must reconnect and resume. */
  close: () => void;
  /** Network-level failure — the hook must reconnect with backoff. */
  fail: (error?: unknown) => void;
};

/** A controllable SSE `Response` for `GET /events/stream` route mocks. */
export function sseConnection(): SseConnection {
  const encoder = new TextEncoder();
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start(streamController) {
      controller = streamController;
    },
  });
  const response = new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
  return {
    response,
    frame: (id, envelope) =>
      controller.enqueue(encoder.encode(`id: ${id}\ndata: ${JSON.stringify(envelope)}\n\n`)),
    heartbeat: () => controller.enqueue(encoder.encode(': heartbeat\n\n')),
    close: () => controller.close(),
    fail: (error) => controller.error(error ?? new Error('stream lost')),
  };
}

/**
 * Behaving-like-the-server tasks route (MT-4.3-03): applies exactly the
 * contract's query parameters (`include_archived`, `priority`, `state`) so
 * tests prove the client sends what it should and renders what returns.
 */
export function tasksServerRoute(pid: string, tasks: unknown[]): Route {
  return {
    method: 'GET',
    match: new RegExp(`/api/v1/projects/${pid}/tasks(\\?|$)`),
    respond: ({ search }) => {
      const params = new URLSearchParams(search);
      const includeArchived = params.get('include_archived') === 'true';
      const priority = params.get('priority');
      const states = params.getAll('state');
      type Row = { priority: string; state: string; archived_at: string | null };
      const filtered = tasks.filter((task) => {
        const row = task as Row;
        return (
          (includeArchived || row.archived_at === null) &&
          (priority === null || row.priority === priority) &&
          (states.length === 0 || states.includes(row.state))
        );
      });
      return jsonResponse(pageOf(filtered));
    },
  };
}

/** Standard board test routes: tasks list, policy, and an SSE stream. */
export function installBoardApi(
  options: {
    pid?: string;
    tasks?: unknown[];
    policy?: unknown;
    sse?: () => Response;
    extraRoutes?: Route[];
  } = {},
): { calls: RecordedCall[]; fetchMock: Mock } {
  const { pid = 'PID00001', tasks = [], policy = makePolicy(), sse, extraRoutes = [] } = options;
  const routes: Route[] = [
    tasksServerRoute(pid, tasks),
    {
      method: 'GET',
      match: new RegExp(`/api/v1/projects/${pid}/policy(\\?|$)`),
      respond: () => jsonResponse(policy),
    },
    ...extraRoutes,
  ];
  if (sse !== undefined) {
    routes.push({
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => sse(),
    });
  }
  return installApi(routes);
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
