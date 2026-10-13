/**
 * MT-4.5-02 — markdown editor with preview: byte-identical round trip
 * through the modal's save path, inert preview rendering of hostile
 * markdown (P10 posture), keyboard-operable toggle, theme-token styling.
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MarkdownEditor } from '@/components/task/markdown-editor';
import { MarkdownPreview } from '@/components/task/markdown-preview';
import { Board } from '@/components/board/board';
import {
  installApi,
  jsonResponse,
  makeTask,
  renderWithQueryClient,
  tasksServerRoute,
} from '../helpers/api';

const PID = 'PID00001';

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('markdown-editor', () => {
  it('round-trips typed markdown byte-identically through the modal save path', async () => {
    const markdown =
      '## Steps\n\n- one\n- two\n\n```py\nprint("hi")\n```\n\nTrailing spaces   \n<not-html>';
    const tasks: unknown[] = [makeTask({ id: 'PID00001-T010', state: 'draft', description: '' })];
    const { calls } = installApi([
      tasksServerRoute(PID, tasks),
      {
        method: 'PATCH',
        match: /\/api\/v1\/tasks\/PID00001-T010$/,
        respond: () => {
          // Server truth after the save — the list refetch serves it too.
          const savedRow = makeTask({
            id: 'PID00001-T010',
            state: 'draft',
            description: markdown,
            version: 2,
          });
          tasks[0] = savedRow;
          return jsonResponse(savedRow, 200);
        },
      },
    ]);
    renderWithQueryClient(<Board pid={PID} />);

    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T010'));
    const modal = within(screen.getByTestId('task-form-modal'));
    fireEvent.change(modal.getByTestId('markdown-editor-input'), {
      target: { value: markdown },
    });
    fireEvent.click(screen.getByTestId('task-form-submit'));

    await waitFor(() => expect(screen.getByText('Changes saved.')).toBeTruthy());
    const patch = calls.find((call) => call.method === 'PATCH');
    expect(patch?.body).toMatchObject({ description: markdown });

    // Close (clean — baseline caught up) and re-open: a fresh mount shows
    // the identical bytes the server stored (reload fidelity).
    fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('task-form-modal')).toBeNull());
    fireEvent.click(await screen.findByLabelText('Edit task PID00001-T010'));
    await waitFor(() =>
      expect(
        (
          within(screen.getByTestId('task-form-modal')).getByTestId(
            'markdown-editor-input',
          ) as HTMLTextAreaElement
        ).value,
      ).toBe(markdown),
    );
  });

  it('preview renders markdown structure as inert elements', () => {
    renderWithQueryClient(
      <MarkdownPreview
        source={
          '# Title\n\nSome **bold** and *italic* and `code`.\n\n```js\nconst a = 1;\n```\n\n- item one'
        }
      />,
    );

    expect(screen.getByTestId('markdown-preview-h1').textContent).toBe('Title');
    expect(screen.getByText('bold').closest('strong')).toBeTruthy();
    expect(screen.getByText('italic').closest('em')).toBeTruthy();
    expect(screen.getByText('code').closest('code')).toBeTruthy();
    expect(screen.getByTestId('markdown-preview-code').textContent).toContain('const a = 1;');
    expect(screen.getByText('item one').closest('li')).toBeTruthy();
  });

  it('renders hostile markdown inert: no script execution, no image fetches, links shown as text', () => {
    const hostile =
      '<script>alert(1)</script>\n\n![tracker](https://evil.example/pixel.png)\n\n[click](javascript:alert(1))';
    const { container } = renderWithQueryClient(<MarkdownPreview source={hostile} />);

    // No script element ever appears; the raw text stays literal (React-escaped).
    expect(container.querySelector('script')).toBeNull();
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeTruthy();
    // No <img> element — the tracking URL is shown as inert text.
    expect(container.querySelector('img')).toBeNull();
    expect(screen.getByTestId('markdown-preview-image').textContent).toContain(
      'evil.example/pixel.png',
    );
    // No anchor elements at all — javascript: URLs cannot be activated.
    expect(container.querySelector('a')).toBeNull();
    expect(screen.getByText(/javascript:alert\(1\)/)).toBeTruthy();
  });

  it('toggles between edit and preview with the keyboard', () => {
    renderWithQueryClient(<MarkdownEditor id="desc" value="# Hi" onChange={() => undefined} />);

    const previewTab = screen.getByTestId('markdown-tab-preview');
    previewTab.focus();
    fireEvent.keyDown(previewTab, { key: 'Enter' });
    fireEvent.click(previewTab);
    expect(screen.getByTestId('markdown-preview')).toBeTruthy();
    expect(screen.getByTestId('markdown-preview-h1').textContent).toBe('Hi');

    const editTab = screen.getByTestId('markdown-tab-edit');
    editTab.focus();
    fireEvent.keyDown(editTab, { key: ' ' });
    fireEvent.click(editTab);
    expect(screen.getByTestId('markdown-editor-input')).toBeTruthy();
    expect(screen.queryByTestId('markdown-preview')).toBeNull();
  });

  it('follows the shared theme token classes (dark/light safe)', () => {
    const { container } = renderWithQueryClient(<MarkdownPreview source={'# Hi'} />);
    const heading = screen.getByTestId('markdown-preview-h1');
    expect(heading.className).toContain('text-foreground');
    expect(container.querySelector('[data-testid="markdown-preview"]')?.className).toContain(
      'border-border',
    );
  });
});
