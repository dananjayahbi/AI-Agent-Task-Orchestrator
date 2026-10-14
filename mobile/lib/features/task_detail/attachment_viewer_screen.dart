import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/read_error_messages.dart';
import 'attachment_providers.dart';
import 'inert_markdown.dart';
import 'untrusted_content_banner.dart';

/// Attachment viewer (Section 14.1 "attachments (view)"; MT-5.7-03):
/// image with pinch-zoom, OCR transcript, and document pages with
/// Section 9.5 pagination — reached from the detail screen's attachment
/// list with the [Attachment] row in hand (deep-link by id is WP-5.9).
///
/// Text-derived panes carry the untrusted-content banner (P10) and
/// render inertly; the server's own banner prefix inside the text is
/// never stripped (Section 9.5).
class AttachmentViewerScreen extends ConsumerWidget {
  const AttachmentViewerScreen({super.key, required this.attachment});

  final Attachment attachment;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AttachmentViewerState state =
        ref.watch(attachmentViewerProvider(attachment.id));
    return Scaffold(
      appBar: AppBar(title: Text(attachment.filename)),
      body: _body(context, ref, state),
    );
  }

  Widget _body(
    BuildContext context,
    WidgetRef ref,
    AttachmentViewerState state,
  ) {
    switch (state.status) {
      case AttachmentViewerStatus.loading:
        return const Center(
          key: ValueKey<String>('attachment-viewer-loading'),
          child: CircularProgressIndicator(),
        );
      case AttachmentViewerStatus.error:
        return _ErrorPane(
          message: friendlyAttachmentErrorMessage(state.error!) ??
              friendlyReadErrorMessage(state.error!),
        );
      case AttachmentViewerStatus.processing:
        return _StatusPane(
          key: const ValueKey<String>('attachment-viewer-processing'),
          icon: Icons.hourglass_top,
          title: 'Still processing',
          detail: 'This attachment has not finished the processing pipeline. '
              'The view refreshes automatically when it becomes ready.',
        );
      case AttachmentViewerStatus.failed:
        final Attachment row = state.attachment ?? attachment;
        return _StatusPane(
          key: const ValueKey<String>('attachment-viewer-failed'),
          icon: Icons.error_outline,
          title: 'Processing failed',
          detail: row.failureReason == null || row.failureReason!.isEmpty
              ? 'The server reported no reason.'
              : row.failureReason!,
        );
      case AttachmentViewerStatus.ready:
        return _tabs(context, ref, state);
    }
  }

  /// Image attachments: Image / OCR tabs (+ description when present).
  /// Documents: Document pages (+ description when present). The
  /// description pane hides gracefully when the provider is disabled
  /// (OQ-07 default — null description simply shows no pane). Content
  /// fetch errors show as a banner above the panes — the tab count
  /// never shifts (the row stays visible, catalog copy only).
  Widget _tabs(
    BuildContext context,
    WidgetRef ref,
    AttachmentViewerState state,
  ) {
    final Attachment row = state.attachment ?? attachment;
    final bool hasDescription =
        row.shortDescription != null && row.shortDescription!.isNotEmpty;
    final List<Widget> panes = <Widget>[];
    final List<Widget> tabs = <Widget>[];
    if (row.isImage) {
      tabs.addAll(<Widget>[
        const Tab(text: 'Image'),
        const Tab(text: 'OCR'),
      ]);
      panes.addAll(<Widget>[
        _ImagePane(state: state),
        _OcrPane(state: state),
      ]);
    } else {
      tabs.add(const Tab(text: 'Document'));
      panes.add(_DocumentPane(state: state));
    }
    if (hasDescription) {
      tabs.add(const Tab(text: 'Description'));
      panes.add(_DescriptionPane(attachment: row));
    }
    return DefaultTabController(
      length: tabs.length,
      child: Column(
        children: <Widget>[
          if (state.error != null)
            _ContentErrorBanner(message: _contentErrorMessage(state)),
          if (tabs.length > 1) TabBar(tabs: tabs),
          if (tabs.length == 1)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Center(child: tabs.first),
            ),
          Expanded(
            child:
                panes.length == 1 ? panes.single : TabBarView(children: panes),
          ),
        ],
      ),
    );
  }

  String _contentErrorMessage(AttachmentViewerState state) {
    final OrchestratorApiException? error = state.error;
    if (error == null) {
      return '';
    }
    return friendlyAttachmentErrorMessage(error) ??
        friendlyReadErrorMessage(error);
  }
}

/// Full-pane friendly error (catalog codes only).
class _ErrorPane extends StatelessWidget {
  const _ErrorPane({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      key: const ValueKey<String>('attachment-viewer-error'),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(message, textAlign: TextAlign.center),
      ),
    );
  }
}

/// Content-fetch error shown beside the known row (catalog copy only).
class _ContentErrorBanner extends StatelessWidget {
  const _ContentErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Container(
      key: const ValueKey<String>('attachment-content-error'),
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        message,
        style: Theme.of(context)
            .textTheme
            .bodySmall
            ?.copyWith(color: scheme.onErrorContainer),
      ),
    );
  }
}

/// Honest non-content state (processing / failed).
class _StatusPane extends StatelessWidget {
  const _StatusPane({
    super.key,
    required this.icon,
    required this.title,
    required this.detail,
  });

  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(icon, size: 48, color: theme.colorScheme.outline),
            const SizedBox(height: 16),
            Text(title, style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(detail, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

/// Image pane: normalized image from `image_base64` with pinch-zoom
/// (InteractiveViewer). The bytes arrive through the auth-aware client.
class _ImagePane extends StatelessWidget {
  const _ImagePane({required this.state});

  final AttachmentViewerState state;

  @override
  Widget build(BuildContext context) {
    final AttachmentContent? content = state.imageContent;
    if (content == null ||
        content.imageBase64 == null ||
        content.imageBase64!.isEmpty) {
      return const Center(
        key: ValueKey<String>('attachment-image-empty'),
        child: Text('No image data.'),
      );
    }
    Uint8List bytes;
    try {
      bytes = base64Decode(content.imageBase64!);
    } on FormatException {
      return const Center(
        key: ValueKey<String>('attachment-image-corrupt'),
        child: Text('The server sent unreadable image data.'),
      );
    }
    return InteractiveViewer(
      key: const ValueKey<String>('attachment-image-pane'),
      maxScale: 8,
      child: Center(
        child: Image.memory(
          bytes,
          key: const ValueKey<String>('attachment-image'),
          fit: BoxFit.contain,
          gaplessPlayback: true,
        ),
      ),
    );
  }
}

/// OCR pane: `text_ocr` transcript plus the layout description —
/// bannered (P10 server prefix preserved) and rendered inertly.
class _OcrPane extends ConsumerWidget {
  const _OcrPane({required this.state});

  final AttachmentViewerState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AttachmentContent? content = state.ocrContent;
    if (content == null) {
      // Load on first view of the tab.
      Future<void>.microtask(() => ref
          .read(attachmentViewerProvider(state.attachment!.id).notifier)
          .loadOcr());
      return const Center(
        key: ValueKey<String>('attachment-ocr-loading'),
        child: CircularProgressIndicator(),
      );
    }
    return ListView(
      key: const ValueKey<String>('attachment-ocr-pane'),
      padding: const EdgeInsets.only(bottom: 16),
      children: <Widget>[
        const UntrustedContentBanner(),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(content.content ?? '',
                  key: const ValueKey<String>('attachment-ocr-text')),
              if (content.description != null &&
                  content.description!.isNotEmpty) ...<Widget>[
                const SizedBox(height: 16),
                Text(
                  'Layout',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 4),
                Text(
                  content.description!,
                  key: const ValueKey<String>('attachment-ocr-layout'),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

/// Document pane: one markdown page per call with Section 9.5
/// `page_number`/`total_pages` navigation and token-count awareness.
class _DocumentPane extends ConsumerWidget {
  const _DocumentPane({required this.state});

  final AttachmentViewerState state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AttachmentContent? content = state.documentContent;
    final int? total = content?.totalPages;
    final int page = state.documentPage;
    return Column(
      children: <Widget>[
        const UntrustedContentBanner(),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: Row(
            children: <Widget>[
              IconButton(
                key: const ValueKey<String>('attachment-page-prev'),
                onPressed: page > 1
                    ? () => ref
                        .read(attachmentViewerProvider(state.attachment!.id)
                            .notifier)
                        .loadDocumentPage(page - 1)
                    : null,
                icon: const Icon(Icons.chevron_left),
              ),
              Expanded(
                child: Text(
                  total == null
                      ? 'Page $page'
                      : 'Page $page of $total'
                          '${content!.tokenCount == null ? '' : ' · ~${content.tokenCount} tokens'}',
                  key: const ValueKey<String>('attachment-page-indicator'),
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.labelLarge,
                ),
              ),
              IconButton(
                key: const ValueKey<String>('attachment-page-next'),
                onPressed: total == null || page < total
                    ? () => ref
                        .read(attachmentViewerProvider(state.attachment!.id)
                            .notifier)
                        .loadDocumentPage(page + 1)
                    : null,
                icon: const Icon(Icons.chevron_right),
              ),
            ],
          ),
        ),
        Expanded(
          child: content == null
              ? state.error != null
                  // A failed content fetch must not spin forever beside
                  // the banner — an honest no-content state instead.
                  ? const Center(
                      key: ValueKey<String>('attachment-document-error'),
                      child: Text('This page could not be loaded.'),
                    )
                  : const Center(
                      key: ValueKey<String>('attachment-document-loading'),
                      child: CircularProgressIndicator(),
                    )
              : ListView(
                  key: const ValueKey<String>('attachment-document-pane'),
                  padding: const EdgeInsets.all(16),
                  children: <Widget>[
                    InertMarkdown(
                      data: content.content ?? '',
                    ),
                  ],
                ),
        ),
      ],
    );
  }
}

/// Description pane (Section 7.2 `description`/`layout_caption`): shown
/// only when the description provider produced one (OQ-07 default).
class _DescriptionPane extends StatelessWidget {
  const _DescriptionPane({required this.attachment});

  final Attachment attachment;

  @override
  Widget build(BuildContext context) {
    return ListView(
      key: const ValueKey<String>('attachment-description-pane'),
      padding: const EdgeInsets.only(bottom: 16),
      children: <Widget>[
        const UntrustedContentBanner(),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            attachment.shortDescription ?? '',
            key: const ValueKey<String>('attachment-description-text'),
          ),
        ),
      ],
    );
  }
}
