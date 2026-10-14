import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'review_providers.dart';

/// Opens the reassign confirmation (MT-5.8-06): plain-language outcome
/// (task returns to `pending`, worker cleared so any eligible agent may
/// claim it — Sections 11.5/8.2) with an **optional** note. There is
/// deliberately no assignee picker: reassign means free re-claim (the
/// plan defines no target-agent selection).
///
/// Confirmation-vs-direct is a parity choice with the web dialog (the
/// plan mandates confirmation only for approve) — recorded in the WP
/// changelog, not presented as plan text.
Future<void> showReassignDialog(
  BuildContext context, {
  required String taskId,
}) {
  return showDialog<void>(
    context: context,
    builder: (BuildContext context) => ReassignDialog(taskId: taskId),
  );
}

class ReassignDialog extends ConsumerStatefulWidget {
  const ReassignDialog({super.key, required this.taskId});

  final String taskId;

  @override
  ConsumerState<ReassignDialog> createState() => _ReassignDialogState();
}

class _ReassignDialogState extends ConsumerState<ReassignDialog> {
  final TextEditingController _controller = TextEditingController();
  late final int _version;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _version = ref.read(reviewProvider(widget.taskId)).task?.version ?? 0;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ReviewState state = ref.watch(reviewProvider(widget.taskId));
    final ThemeData theme = Theme.of(context);

    return AlertDialog(
      title: const Text('Reassign task?'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              key: const ValueKey<String>('review-reassign-copy'),
              'The task returns to pending and the current worker is '
              'cleared, so any eligible agent may claim it.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            TextField(
              key: const ValueKey<String>('review-reassign-note-field'),
              controller: _controller,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Optional note for the next worker',
              ),
            ),
          ],
        ),
      ),
      actions: <Widget>[
        TextButton(
          key: const ValueKey<String>('review-reassign-cancel'),
          onPressed: _submitting ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          key: const ValueKey<String>('review-reassign-confirm'),
          onPressed: (_submitting || !state.actionsEnabled) ? null : _submit,
          child: _submitting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Reassign'),
        ),
      ],
    );
  }

  Future<void> _submit() async {
    if (_submitting) {
      return;
    }
    setState(() => _submitting = true);
    await ref.read(reviewProvider(widget.taskId).notifier).reassign(
          // Optional: an empty note stays empty (only request changes
          // requires one — Section 8.2 T16 guard).
          note: _controller.text.trim(),
          version: _version,
        );
    if (mounted) {
      Navigator.of(context).pop();
    }
  }
}
