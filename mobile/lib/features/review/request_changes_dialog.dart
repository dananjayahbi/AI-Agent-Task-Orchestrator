import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'dictation_service.dart';
import 'review_providers.dart';

/// Opens the request-changes dialog (MT-5.8-05): a required note with
/// typed input and an on-device dictate affordance (T16 guard: only
/// request changes requires a note).
Future<void> showRequestChangesDialog(
  BuildContext context, {
  required String taskId,
}) {
  return showDialog<void>(
    context: context,
    builder: (BuildContext context) => RequestChangesDialog(taskId: taskId),
  );
}

class RequestChangesDialog extends ConsumerStatefulWidget {
  const RequestChangesDialog({super.key, required this.taskId});

  final String taskId;

  @override
  ConsumerState<RequestChangesDialog> createState() =>
      _RequestChangesDialogState();
}

class _RequestChangesDialogState extends ConsumerState<RequestChangesDialog> {
  final TextEditingController _controller = TextEditingController();
  late final int _version;
  late final DictationService _dictation;
  bool _submitting = false;
  bool _dictating = false;
  String? _dictationMessage;

  @override
  void initState() {
    super.initState();
    // The version the sheet rendered when the dialog opened (FR-TSK-06
    // optimistic lock — the decision is bound to what the user saw).
    _version = ref.read(reviewProvider(widget.taskId)).task?.version ?? 0;
    _dictation = ref.read(dictationServiceProvider);
  }

  @override
  void dispose() {
    if (_dictating) {
      // Best-effort teardown: never leave the recognizer running
      // behind a dismissed dialog (no ref use — capture, not read).
      _dictation.stop();
    }
    _controller.dispose();
    super.dispose();
  }

  bool get _hasText => _controller.text.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    final ReviewState state = ref.watch(reviewProvider(widget.taskId));
    final ThemeData theme = Theme.of(context);
    final bool canSubmit = _hasText && !_submitting && state.actionsEnabled;

    return PopScope(
      canPop: !_hasText,
      onPopInvokedWithResult: (bool didPop, Object? result) {
        if (didPop) {
          return;
        }
        // Discard safety (MT-5.8-05): dismissing with uncommitted text
        // confirms first — recorded UX decision in the WP changelog.
        _confirmDiscard();
      },
      child: AlertDialog(
        title: const Text('Request changes'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                key: const ValueKey<String>('review-request-note-hint'),
                'The note is required — it becomes the feedback the next '
                'coder sees (task returns to pending).',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              TextField(
                key: const ValueKey<String>('review-request-note-field'),
                controller: _controller,
                readOnly: _dictating,
                minLines: 3,
                maxLines: 6,
                onChanged: (_) => setState(() {}),
                decoration: const InputDecoration(
                  border: OutlineInputBorder(),
                  hintText: 'What should change?',
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: <Widget>[
                  FilledButton.tonalIcon(
                    key: ValueKey<String>(_dictating
                        ? 'review-request-stop-dictating'
                        : 'review-request-dictate'),
                    onPressed: _submitting ? null : _toggleDictation,
                    icon: Icon(_dictating ? Icons.mic_off : Icons.mic_none),
                    label: Text(_dictating ? 'Stop dictating' : 'Dictate'),
                  ),
                  const SizedBox(width: 8),
                  if (_dictating)
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        key: const ValueKey<String>(
                            'review-request-dictating-indicator'),
                        strokeWidth: 2,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                key: const ValueKey<String>('review-request-dictation-hint'),
                'On-device speech-to-text — audio is never uploaded; you can '
                'edit the text before sending.',
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
              if (_dictationMessage != null)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    key: const ValueKey<String>(
                        'review-request-dictation-unavailable'),
                    _dictationMessage!,
                    style: theme.textTheme.bodySmall
                        ?.copyWith(color: theme.colorScheme.error),
                  ),
                ),
            ],
          ),
        ),
        actions: <Widget>[
          TextButton(
            key: const ValueKey<String>('review-request-cancel'),
            onPressed: _submitting ? null : () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            key: const ValueKey<String>('review-request-submit'),
            onPressed: canSubmit ? _submit : null,
            child: _submitting
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Send'),
          ),
        ],
      ),
    );
  }

  Future<void> _toggleDictation() async {
    final DictationService service = _dictation;
    if (_dictating) {
      await service.stop();
      if (mounted) {
        setState(() => _dictating = false);
      }
      return;
    }
    setState(() => _dictationMessage = null);
    try {
      await service.start(
        onText: (String text) {
          if (mounted) {
            setState(() {
              _controller.value = TextEditingValue(
                text: text,
                selection: TextSelection.collapsed(offset: text.length),
              );
            });
          }
        },
        onEnded: () {
          if (mounted) {
            setState(() => _dictating = false);
          }
        },
      );
      if (mounted) {
        setState(() => _dictating = true);
      }
    } on DictationUnavailableException catch (error) {
      if (mounted) {
        setState(() {
          _dictating = false;
          _dictationMessage = error.reason == 'permission'
              ? 'Microphone permission denied — type your note instead.'
              : 'Dictation unavailable on this device — type your note '
                  'instead.';
        });
      }
    }
  }

  Future<void> _confirmDiscard() async {
    final bool discard = await showDialog<bool>(
          context: context,
          builder: (BuildContext context) => AlertDialog(
            title: const Text('Discard note?'),
            content: const Text('Your note will be lost.'),
            actions: <Widget>[
              TextButton(
                key: const ValueKey<String>('review-request-discard-keep'),
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Keep editing'),
              ),
              FilledButton(
                key: const ValueKey<String>('review-request-discard-confirm'),
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Discard'),
              ),
            ],
          ),
        ) ??
        false;
    if (discard && mounted) {
      Navigator.of(context).pop();
    }
  }

  Future<void> _submit() async {
    final String note = _controller.text.trim();
    if (note.isEmpty || _submitting) {
      return; // T16 guard — whitespace-only counts as empty.
    }
    setState(() => _submitting = true);
    await ref.read(reviewProvider(widget.taskId).notifier).requestChanges(
          note: note,
          version: _version,
        );
    if (mounted) {
      Navigator.of(context).pop();
    }
  }
}
