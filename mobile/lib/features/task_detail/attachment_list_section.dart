import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../app/routes.dart';
import '../../core/api/read_error_messages.dart';
import 'attachment_providers.dart';
import 'task_detail_providers.dart';

/// The attachments region of the Task detail screen (Section 14.1;
/// MT-5.7-03 entry points): one row per attachment with its
/// `processing_status` badge (Section 7.2); a tap opens the viewer.
class AttachmentListSection extends ConsumerWidget {
  const AttachmentListSection({super.key, required this.taskId});

  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AttachmentListState state = ref.watch(attachmentListProvider(taskId));
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Attachments', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          _body(context, ref, state),
        ],
      ),
    );
  }

  Widget _body(BuildContext context, WidgetRef ref, AttachmentListState state) {
    switch (state.status) {
      case TaskDetailStatus.loading:
        return const Padding(
          key: ValueKey<String>('attachment-list-loading'),
          padding: EdgeInsets.all(12),
          child: Center(child: CircularProgressIndicator()),
        );
      case TaskDetailStatus.error:
        return Row(
          children: <Widget>[
            Expanded(
              child: Text(
                friendlyReadErrorMessage(state.error!),
                key: const ValueKey<String>('attachment-list-error'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            TextButton(
              key: const ValueKey<String>('attachment-list-retry'),
              onPressed: () =>
                  ref.read(attachmentListProvider(taskId).notifier).load(),
              child: const Text('Retry'),
            ),
          ],
        );
      case TaskDetailStatus.ready:
        if (state.attachments.isEmpty) {
          return Text(
            'No attachments.',
            key: const ValueKey<String>('attachment-list-empty'),
            style: Theme.of(context)
                .textTheme
                .bodyMedium
                ?.copyWith(color: Theme.of(context).colorScheme.outline),
          );
        }
        return Column(
          children: <Widget>[
            for (final Attachment attachment in state.attachments)
              _AttachmentTile(attachment: attachment),
          ],
        );
    }
  }
}

class _AttachmentTile extends StatelessWidget {
  const _AttachmentTile({required this.attachment});

  final Attachment attachment;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: ListTile(
        key: ValueKey<String>('attachment-tile-${attachment.id}'),
        leading: Icon(
          attachment.isImage
              ? Icons.image_outlined
              : Icons.description_outlined,
          color: theme.colorScheme.outline,
        ),
        title: Text(attachment.filename),
        subtitle: Text(
          '${attachmentSizeLabel(attachment.size)} · '
          '${attachmentStatusLabel(attachment.processingStatus)}',
          key: ValueKey<String>('attachment-status-${attachment.id}'),
        ),
        trailing: const Icon(Icons.chevron_right),
        // Route handoff: the viewer owns the content; the list passes
        // the attachment row (deep-link readiness by id — WP-5.9).
        onTap: () => Navigator.pushNamed(
          context,
          AppRoutes.attachmentViewer,
          arguments: attachment,
        ),
      ),
    );
  }
}

/// Human label for the Section 7.2 `processing_status` values.
String attachmentStatusLabel(String status) {
  switch (status) {
    case 'uploaded':
      return 'Queued';
    case 'processing':
      return 'Processing';
    case 'ready':
      return 'Ready';
    case 'failed':
      return 'Failed';
    default:
      return status;
  }
}

/// Byte-size label for the list subtitle.
String attachmentSizeLabel(int sizeBytes) {
  if (sizeBytes < 1024) {
    return '$sizeBytes B';
  }
  if (sizeBytes < 1024 * 1024) {
    return '${(sizeBytes / 1024).toStringAsFixed(1)} KB';
  }
  return '${(sizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
}
