/**
 * MT-4.5-06 — publish gating: the WP-4.5 acceptance (three attachments
 * reach `pending` only when all report `ready`, or after an explicit
 * override), live gating from `attachment.ready|failed` events, the T2
 * required-field/dependency guards surfacing before the send, the
 * transport seam receiving the client's `version`, and the conflict /
 * catalog error mappings (Sections 8.2, 13.3).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { Board } from '@/components/board/board';
import { TaskFormModal } from '@/components/task/task-form-modal';
import type { Task } from '@/lib/api/generated/types.gen';
import { evaluatePublishGate } from '@/lib/task/publish-gate';
import { publishUnavailableNotice } from '@/lib/task/publish-seam';
import type { PublishRequest, PublishTransport } from '@/lib/task/publish-seam';
import {
  installApi,
  jsonResponse,
  makeEventEnvelope,
  makePolicy,
  makeTask,
  pageOf,
  renderWithQueryClient,
  sseConnection,
  tasksServerRoute,
} from '../helpers/api';
import type { Route } from '../helpers/api';

const PID = 'PID00001';

beforeEach(() => {
  vi.unstubAllGlobals();
});

function makeAttachment(id: string, status: string, extra: Record<string, unknown> = {}) {
  return {
    id,
    task_id: 'PID00001-T040',
    filename: `${id}.bin`,
    mime_type: 'text/plain',
    size: 100,
    is_image: false,
    processing_status: status,
    failure_reason: null,
    token_count: null,
    ...extra,
  };
}

/** Shared routes: board list, policy, SSE stream, attachments list. */
function baseRoutes(task: unknown, attachments: unknown[], stream: SseLike): Route[] {
  return [
    tasksServerRoute(PID, [task]),
    {
      method: 'GET',
      match: new RegExp(`/api/v1/projects/${PID}/policy(\\?|$)`),
      respond: () => jsonResponse(makePolicy()),
    },
    {
      method: 'GET',
      match: /\/api\/v1\/events\/stream(\?|$)/,
      respond: () => stream.response,
    },
    {
      method: 'GET',
      match: /\/api\/v1\/tasks\/PID00001-T040\/attachments(\?|$)/,
      respond: () => jsonResponse(pageOf(attachments)),
    },
  ];
}

type SseLike = ReturnType<typeof sseConnection>;

function harness(options: {
  task?: Record<string, unknown>;
  attachments?: unknown[];
  extraRoutes?: Route[];
}) {
  const task = options.task ?? makeTask({ id: 'PID00001-T040', state: 'draft', version: 3 });
  const stream = sseConnection();
  const { calls } = installApi([
    ...baseRoutes(task, options.attachments ?? [], stream),
    ...(options.extraRoutes ?? []),
  ]);
  return {
    calls,
    emit: (envelope: unknown) => stream.frame(Math.floor(Math.random() * 1_000_000) + 1, envelope),
    render: () => renderWithQueryClient(<Board pid={PID} />),
  };
}

async function openEditor() {
  fireEvent.click(await screen.findByLabelText('Edit task PID00001-T040'));
  await waitFor(() => expect(screen.getByTestId('publish-action')).toBeTruthy());
  // The gate flips from `attachments_loading` to real blockers once the
  // list resolves — wait so assertions see the settled state.
  await waitFor(() =>
    expect(screen.queryByTestId('publish-blocker-attachments_loading')).toBeNull(),
  );
}

// Board + modal wrapper: mirrors `Board`'s entry points but injects the
// publish seam into `TaskFormModal` (the production default is absent).
function BoardWithSeam({ transport }: { transport: PublishTransport }) {
  const [open, setOpen] = useState(false);
  const [task, setTask] = useState<Task | null>(null);
  return (
    <>
      <button
        type="button"
        data-testid="seam-open"
        onClick={() => {
          setTask(makeTask({ id: 'PID00001-T040', state: 'draft', version: 3 }));
          setOpen(true);
        }}
      >
        open
      </button>
      <TaskFormModal
        pid={PID}
        task={task}
        open={open}
        onOpenChange={setOpen}
        onSaved={(created) => setTask(created)}
        publishTransport={transport}
      />
    </>
  );
}

/** Renders the seam wrapper over the same fixture routes. */
function renderWithSeam(
  transport: PublishTransport,
  options: { task?: Record<string, unknown>; attachments?: unknown[] },
) {
  const task = options.task ?? makeTask({ id: 'PID00001-T040', state: 'draft', version: 3 });
  const stream = sseConnection();
  installApi(baseRoutes(task, options.attachments ?? [], stream));
  return renderWithQueryClient(<BoardWithSeam transport={transport} />);
}

describe('publish-gating', () => {
  it('blocks publish while any of three attachments is non-ready and unblocks on the final ready event', async () => {
    const h = harness({
      attachments: [
        makeAttachment('a1', 'ready'),
        makeAttachment('a2', 'processing'),
        makeAttachment('a3', 'uploaded'),
      ],
    });
    h.render();
    await openEditor();

    const modal = within(screen.getByTestId('task-form-modal'));
    expect(modal.getByTestId('publish-blocker-attachments_pending').textContent).toContain('2');
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', true);

    // Live gating: the second file reports ready — still one pending.
    h.emit(
      makeEventEnvelope({
        type: 'attachment.ready',
        task_id: 'PID00001-T040',
        data: { attachment_id: 'a2' },
      }),
    );
    await waitFor(() =>
      expect(modal.getByTestId('publish-blocker-attachments_pending').textContent).toContain('1'),
    );
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', true);

    // The final ready event clears the gate — no manual refresh.
    h.emit(
      makeEventEnvelope({
        type: 'attachment.ready',
        task_id: 'PID00001-T040',
        data: { attachment_id: 'a3' },
      }),
    );
    await waitFor(() =>
      expect(screen.queryByTestId('publish-blocker-attachments_pending')).toBeNull(),
    );
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', false);
  });

  it('sends T2 through the seam with the client version once all three report ready', async () => {
    const sent: PublishRequest[] = [];
    renderWithSeam(
      async (request) => {
        sent.push(request);
      },
      {
        attachments: [
          makeAttachment('a1', 'ready'),
          makeAttachment('a2', 'ready'),
          makeAttachment('a3', 'ready'),
        ],
      },
    );
    fireEvent.click(await screen.findByTestId('seam-open'));
    await waitFor(() => expect(screen.getByTestId('publish-action')).toBeTruthy());
    await waitFor(() =>
      expect(screen.queryByTestId('publish-blocker-attachments_loading')).toBeNull(),
    );

    fireEvent.click(screen.getByTestId('publish-button'));
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toEqual({ taskId: 'PID00001-T040', version: 3, override: false });
    await waitFor(() =>
      expect(screen.getByTestId('publish-notice').getAttribute('data-kind')).toBe('success'),
    );
    expect(screen.getByTestId('publish-notice').textContent).toContain('Pending');
  });

  it('offers the explicit override only for attachment blockers and sends override: true', async () => {
    const sent: PublishRequest[] = [];
    renderWithSeam(
      async (request) => {
        sent.push(request);
      },
      {
        attachments: [makeAttachment('a1', 'ready'), makeAttachment('a2', 'processing')],
      },
    );
    fireEvent.click(await screen.findByTestId('seam-open'));
    await waitFor(() => expect(screen.getByTestId('publish-action')).toBeTruthy());
    await waitFor(() =>
      expect(screen.queryByTestId('publish-blocker-attachments_loading')).toBeNull(),
    );

    // Blocked by default; the override is never pre-selected.
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', true);
    expect(screen.getByTestId('publish-override')).toHaveProperty('checked', false);

    fireEvent.click(screen.getByTestId('publish-override'));
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', false);
    fireEvent.click(screen.getByTestId('publish-button'));

    await waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toMatchObject({ override: true, version: 3 });
  });

  it('blocks on a failed attachment with its pipeline reason and clears via the failed event path', async () => {
    const h = harness({
      attachments: [
        makeAttachment('a1', 'ready'),
        makeAttachment('a2', 'failed', { failure_reason: 'Checksum mismatch after download.' }),
      ],
    });
    h.render();
    await openEditor();

    const modal = within(screen.getByTestId('task-form-modal'));
    expect(modal.getByTestId('publish-blocker-attachments_failed').textContent).toContain(
      'Checksum mismatch after download.',
    );
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', true);
  });

  it('surfaces the required-field and dependency guards before any send', async () => {
    const h = harness({
      task: makeTask({ id: 'PID00001-T040', state: 'draft', title: '   ', version: 1 }),
      attachments: [],
      extraRoutes: [
        {
          method: 'GET',
          match: /\/api\/v1\/tasks\/PID00001-T007(\?|$)/,
          respond: () => jsonResponse(makeTask({ id: 'PID00001-T007', state: 'pending' })),
        },
      ],
    });
    // depends_on fixture: patch the board task row.
    h.render();
    await openEditor();

    // Blank title blocks (T2 required fields).
    expect(screen.getByTestId('publish-blocker-missing_title')).toBeTruthy();
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', true);
  });

  it('shows the explicit unavailable notice when no transition consumer is wired', async () => {
    harness({
      attachments: [makeAttachment('a1', 'ready')],
    }).render();
    await openEditor();

    // Seam absent: the gate passes, publish runs the validated action
    // and lands on the explicit notice — no silent no-op (WP-4.4 rule).
    await waitFor(() =>
      expect(screen.queryByTestId('publish-blocker-attachments_loading')).toBeNull(),
    );
    expect(screen.getByTestId('publish-button')).toHaveProperty('disabled', false);
    fireEvent.click(screen.getByTestId('publish-button'));
    await waitFor(() =>
      expect(screen.getByTestId('publish-notice').textContent).toBe(
        publishUnavailableNotice('PID00001-T040'),
      ),
    );
  });

  it('maps VERSION_CONFLICT from the seam to friendly refresh guidance', async () => {
    renderWithSeam(
      async () => {
        const error = Object.assign(new Error('stale'), {
          code: 'VERSION_CONFLICT',
          correlationId: 'corr-1',
        });
        throw error;
      },
      { attachments: [makeAttachment('a1', 'ready')] },
    );
    fireEvent.click(await screen.findByTestId('seam-open'));
    await waitFor(() => expect(screen.getByTestId('publish-action')).toBeTruthy());
    await waitFor(() =>
      expect(screen.queryByTestId('publish-blocker-attachments_loading')).toBeNull(),
    );

    fireEvent.click(screen.getByTestId('publish-button'));
    await waitFor(() =>
      expect(screen.getByTestId('publish-notice').textContent).toBe(
        'Someone else updated this first. Reload to get the latest version, then retry.',
      ),
    );
    expect(screen.getByTestId('publish-notice').getAttribute('data-kind')).toBe('error');
  });

  it('pins the pure gate: dirty forms and non-draft states never pass; override never clears them', () => {
    const ready = [makeAttachment('a1', 'ready')];
    const base = {
      state: 'draft',
      dirty: false,
      titleValid: true,
      attachments: ready as never,
      dependencies: [] as never,
    };

    expect(evaluatePublishGate(base).canPublish).toBe(true);

    const dirty = evaluatePublishGate({ ...base, dirty: true });
    expect(dirty.canPublish).toBe(false);
    expect(dirty.overrideCovers).toBe(false); // override never clears unsaved edits

    const titled = evaluatePublishGate({ ...base, titleValid: false });
    expect(titled.blockers.some((b) => b.kind === 'missing_title')).toBe(true);
    expect(titled.overrideCovers).toBe(false);

    const pendingOnly = evaluatePublishGate({
      ...base,
      attachments: [makeAttachment('a1', 'processing')] as never,
    });
    expect(pendingOnly.overrideCovers).toBe(true); // attachment blockers are override territory

    const unmetDep = evaluatePublishGate({
      ...base,
      dependencies: [{ id: 'PID00001-T009', status: 'incomplete' }] as never,
    });
    expect(unmetDep.blockers.some((b) => b.kind === 'dependencies_unmet')).toBe(true);
    expect(unmetDep.overrideCovers).toBe(false);
  });
});
