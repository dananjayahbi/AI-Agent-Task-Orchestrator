import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';
import '../../core/realtime/orchestrator_event.dart';
import '../../core/realtime/realtime_providers.dart';
import '../../core/realtime/sse_client.dart';
import 'task_detail_providers.dart';
import 'task_detail_repository.dart';

/// Read-side repository for one attachment (MT-5.7-03) — generated-client
/// operations over the shared OpenAPI schema (NFR-11).
abstract class AttachmentRepository {
  /// `GET /attachments/{id}` — the row with `processing_status` etc.
  Future<Attachment> fetchAttachment(String attachmentId);

  /// `GET /attachments/{id}/content?format=&page=` — Section 9.5's
  /// retrieval table; one page per call for paginated formats.
  Future<AttachmentContent> fetchContent(
    String attachmentId, {
    required String format,
    int page = 1,
  });
}

/// Generated-client implementation. The image path is an auth-aware
/// JSON fetch through the shared client (the base64 payload rides the
/// same authenticated Dio as every other call — the token interceptor
/// owns the header, and no token value is touched here).
class GeneratedAttachmentRepository implements AttachmentRepository {
  GeneratedAttachmentRepository(this._client);

  final OrchestratorClient _client;

  @override
  Future<Attachment> fetchAttachment(String attachmentId) async {
    try {
      final Response<Attachment> response =
          await _client.api.retrieveAttachment(id: attachmentId);
      final Attachment? attachment = response.data;
      if (attachment == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Attachment response carried no body.',
          retryable: true,
        );
      }
      return attachment;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<AttachmentContent> fetchContent(
    String attachmentId, {
    required String format,
    int page = 1,
  }) async {
    try {
      final Response<AttachmentContent> response =
          await _client.api.retrieveAttachmentContent(
        id: attachmentId,
        format: format,
        page: page,
      );
      final AttachmentContent? content = response.data;
      if (content == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Attachment content response carried no body.',
          retryable: true,
        );
      }
      return content;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

final Provider<AttachmentRepository> attachmentRepositoryProvider =
    Provider<AttachmentRepository>(
  (Ref ref) => GeneratedAttachmentRepository(ref.watch(apiClientProvider)),
);

/// Section 9.5 wire formats the viewer requests explicitly (the MT risk
/// note: the app always displays images, so it never relies on `auto`'s
/// capability guessing).
abstract final class AttachmentFormats {
  static const String image = 'image_base64';
  static const String ocr = 'text_ocr';
  static const String markdown = 'markdown';
}

/// Friendly, catalog-only copy for the two attachment-specific Section
/// 9.2 codes (Section 20.4 item 5: no invented codes; the raw server
/// message never reaches the UI — Section 12.4).
String? friendlyAttachmentErrorMessage(OrchestratorApiException error) {
  switch (error.code) {
    case CodeEnum.ATTACHMENT_NOT_READY:
      return 'This attachment is still being processed — try again shortly.';
    case CodeEnum.ATTACHMENT_UNSUPPORTED_FORMAT:
      return 'This attachment type cannot be displayed.';
    default:
      return null;
  }
}

/// Section 9.6 attachment lifecycle types (catalog, Section 20.4 item 6).
const Set<String> attachmentLifecycleEvents = <String>{
  'attachment.processing',
  'attachment.ready',
  'attachment.failed',
};

/// Viewer state of one attachment (Section 20.3 states plus the
/// Section 9.5 processing lifecycle).
enum AttachmentViewerStatus {
  /// Row and content are loading for the first time.
  loading,

  /// Content is displayed for the active tab/page.
  ready,

  /// `processing_status` is uploaded/processing — content requests would
  /// answer ATTACHMENT_NOT_READY; the row refreshes live (Section 9.6).
  processing,

  /// `processing_status` is failed — the row's failure reason explains
  /// why (Section 7.2 `failure_detail`).
  failed,

  /// The row load failed; catalog codes drive the friendly copy.
  error,
}

/// The full attachment viewer state.
class AttachmentViewerState {
  const AttachmentViewerState({
    required this.status,
    this.attachment,
    this.imageContent,
    this.ocrContent,
    this.documentPage = 1,
    this.documentContent,
    this.error,
  });

  const AttachmentViewerState.loading()
      : this(status: AttachmentViewerStatus.loading);

  const AttachmentViewerState.ready({
    required Attachment attachment,
    AttachmentContent? imageContent,
    AttachmentContent? ocrContent,
    int documentPage = 1,
    AttachmentContent? documentContent,
  }) : this(
          status: AttachmentViewerStatus.ready,
          attachment: attachment,
          imageContent: imageContent,
          ocrContent: ocrContent,
          documentPage: documentPage,
          documentContent: documentContent,
        );

  const AttachmentViewerState.processing(Attachment attachment)
      : this(status: AttachmentViewerStatus.processing, attachment: attachment);

  const AttachmentViewerState.failed(Attachment attachment)
      : this(status: AttachmentViewerStatus.failed, attachment: attachment);

  const AttachmentViewerState.error(OrchestratorApiException error)
      : this(status: AttachmentViewerStatus.error, error: error);

  final AttachmentViewerStatus status;
  final Attachment? attachment;

  /// Cached per-tab content (each one page per call — Section 9.5;
  /// memory only, never persisted off-device — Section 12.4).
  final AttachmentContent? imageContent;
  final AttachmentContent? ocrContent;
  final int documentPage;
  final AttachmentContent? documentContent;

  /// A row or content load failed. With a row in hand the viewer shows
  /// it beside the tabs; without one it is the full-screen error state
  /// (catalog codes only — Section 20.4 item 5).
  final OrchestratorApiException? error;

  /// Ready-state copy with cached content merged in.
  AttachmentViewerState _copyWith({
    Attachment? attachment,
    AttachmentContent? imageContent,
    AttachmentContent? ocrContent,
    int? documentPage,
    AttachmentContent? documentContent,
  }) =>
      AttachmentViewerState.ready(
        attachment: attachment ?? this.attachment!,
        imageContent: imageContent ?? this.imageContent,
        ocrContent: ocrContent ?? this.ocrContent,
        documentPage: documentPage ?? this.documentPage,
        documentContent: documentContent ?? this.documentContent,
      );

  /// Ready-state copy recording a content/row error beside the row.
  AttachmentViewerState _copyWithError(OrchestratorApiException error) =>
      status == AttachmentViewerStatus.ready && attachment != null
          ? AttachmentViewerState.ready(
              attachment: attachment!,
              imageContent: imageContent,
              ocrContent: ocrContent,
              documentPage: documentPage,
              documentContent: documentContent,
            )._withError(error)
          : AttachmentViewerState.error(error);

  AttachmentViewerState _withError(OrchestratorApiException error) =>
      AttachmentViewerState(
        status: status,
        attachment: attachment,
        imageContent: imageContent,
        ocrContent: ocrContent,
        documentPage: documentPage,
        documentContent: documentContent,
        error: error,
      );
}

/// Attachment viewer state holder (MT-5.7-03).
///
/// Loads the row, then the explicit-format content the screen shows
/// (image via `image_base64`, OCR via `text_ocr`, document pages via
/// `markdown` — one page per call, Section 9.5). While foregrounded, the
/// Section 9.6 `attachment.processing|ready|failed` events refresh the
/// row through the shared [SseClient] (consumed, never forked); the
/// viewer requires the unlocked session and never caches text off-device
/// (Section 12.4 — state lives in memory only).
class AttachmentViewerNotifier
    extends AutoDisposeFamilyNotifier<AttachmentViewerState, String> {
  StreamSubscription<OrchestratorEvent>? _eventsSub;

  /// The owning task id, learned from the row — belts the live
  /// lifecycle subscription once known (events carry `task_id`).
  String? _taskId;

  int _loadToken = 0;

  @override
  AttachmentViewerState build(String attachmentId) {
    final SseClient client = ref.read(sseClientProvider);
    _eventsSub = client.events
        .listen((OrchestratorEvent event) => _onEvent(attachmentId, event));
    ref.onDispose(() {
      _eventsSub?.cancel();
      _eventsSub = null;
    });
    Future<void>.microtask(() => load(attachmentId));
    return const AttachmentViewerState.loading();
  }

  /// Loads the row and the first content for the attachment's kind.
  Future<void> load(String attachmentId) async {
    final int token = ++_loadToken;
    try {
      final AttachmentRepository repository =
          ref.read(attachmentRepositoryProvider);
      final Attachment attachment =
          await repository.fetchAttachment(attachmentId);
      if (token != _loadToken) {
        return;
      }
      _taskId = attachment.taskId;
      state = _statusState(attachment);
      await _loadInitialContent(attachment, repository, token);
    } on OrchestratorApiException catch (error) {
      if (token == _loadToken) {
        state = AttachmentViewerState.error(error);
      }
    }
  }

  /// Maps `processing_status` onto the viewer state (Section 7.2
  /// values; an unknown newer-server value reads as not-ready — honest,
  /// never pretending content exists).
  AttachmentViewerState _statusState(Attachment attachment) {
    switch (attachment.processingStatus) {
      case 'ready':
        return AttachmentViewerState.ready(attachment: attachment);
      case 'failed':
        return AttachmentViewerState.failed(attachment);
      case 'uploaded':
      case 'processing':
        return AttachmentViewerState.processing(attachment);
      default:
        return AttachmentViewerState.processing(attachment);
    }
  }

  Future<void> _loadInitialContent(
    Attachment attachment,
    AttachmentRepository repository,
    int token,
  ) async {
    if (attachment.processingStatus != 'ready') {
      return;
    }
    if (attachment.isImage) {
      await _fetchImage(attachment, repository, token);
    } else {
      await _fetchDocumentPage(attachment, repository, page: 1, token: token);
    }
  }

  /// Image tab: `image_base64` through the auth-aware client.
  Future<void> _fetchImage(
    Attachment attachment,
    AttachmentRepository repository,
    int token,
  ) async {
    try {
      final AttachmentContent content = await repository.fetchContent(
        attachment.id,
        format: AttachmentFormats.image,
      );
      if (token == _loadToken) {
        state = state._copyWith(imageContent: content);
      }
    } on DioException catch (error) {
      _contentFailed(OrchestratorApiException.of(error), token);
    } on OrchestratorApiException catch (error) {
      _contentFailed(error, token);
    }
  }

  /// OCR tab: `text_ocr` — transcript plus the layout description
  /// (Section 9.5), both server-prefixed with the untrusted banner
  /// (P10) which this client never strips. Loaded on demand once.
  Future<void> loadOcr() async {
    final Attachment? attachment = state.attachment;
    if (attachment == null ||
        state.ocrContent != null ||
        state.status != AttachmentViewerStatus.ready) {
      return;
    }
    final int token = ++_loadToken;
    try {
      final AttachmentContent content = await ref
          .read(attachmentRepositoryProvider)
          .fetchContent(attachment.id, format: AttachmentFormats.ocr);
      if (token == _loadToken) {
        state = state._copyWith(ocrContent: content);
      }
    } on DioException catch (error) {
      _contentFailed(OrchestratorApiException.of(error), token);
    } on OrchestratorApiException catch (error) {
      _contentFailed(error, token);
    }
  }

  /// Document tab: one `markdown` page per call (Section 9.5 pagination
  /// — prefetch only the visible page, RISK-13).
  Future<void> loadDocumentPage(int page) async {
    final Attachment? attachment = state.attachment;
    if (attachment == null || state.status != AttachmentViewerStatus.ready) {
      return;
    }
    final int token = ++_loadToken;
    await _fetchDocumentPage(
      attachment,
      ref.read(attachmentRepositoryProvider),
      page: page,
      token: token,
    );
  }

  Future<void> _fetchDocumentPage(
    Attachment attachment,
    AttachmentRepository repository, {
    required int page,
    required int token,
  }) async {
    try {
      final AttachmentContent content = await repository.fetchContent(
        attachment.id,
        format: AttachmentFormats.markdown,
        page: page,
      );
      if (token == _loadToken) {
        state = state._copyWith(
          documentPage: content.pageNumber ?? page,
          documentContent: content,
        );
      }
    } on DioException catch (error) {
      _contentFailed(OrchestratorApiException.of(error), token);
    } on OrchestratorApiException catch (error) {
      _contentFailed(error, token);
    }
  }

  /// Content failures never replace the known row: the error is recorded
  /// beside it (catalog codes only — Section 20.4 item 5).
  void _contentFailed(OrchestratorApiException error, int token) {
    if (token != _loadToken) {
      return;
    }
    state = state._copyWithError(error);
  }

  void _onEvent(String attachmentId, OrchestratorEvent event) {
    if (!attachmentLifecycleEvents.contains(event.type)) {
      return; // Not an attachment lifecycle event (Section 9.6 catalog).
    }
    final Object? id = event.data?['attachment_id'];
    if (id != attachmentId) {
      return;
    }
    if (_taskId != null && event.taskId != null && event.taskId != _taskId) {
      return; // An attachment id cannot cross tasks; belt and braces.
    }
    _refreshRow(attachmentId);
  }

  /// Live row refresh on lifecycle events (foreground-only: the shared
  /// client pauses with the app, Section 14.2). A `ready` transition
  /// re-runs the status mapping, which loads the first content.
  Future<void> _refreshRow(String attachmentId) async {
    try {
      final AttachmentRepository repository =
          ref.read(attachmentRepositoryProvider);
      final Attachment attachment =
          await repository.fetchAttachment(attachmentId);
      _taskId = attachment.taskId;
      state = _statusState(attachment);
      await _loadInitialContent(attachment, repository, _loadToken);
    } on OrchestratorApiException {
      // Keep the current view; the next event or manual retry reconciles.
    }
  }
}

/// One viewer state per attachment id.
final AutoDisposeNotifierProviderFamily<AttachmentViewerNotifier,
        AttachmentViewerState, String> attachmentViewerProvider =
    AutoDisposeNotifierProviderFamily<AttachmentViewerNotifier,
        AttachmentViewerState, String>(AttachmentViewerNotifier.new);

/// The task's attachment list (the detail screen's entry points).
class AttachmentListState {
  const AttachmentListState({
    required this.status,
    this.attachments = const <Attachment>[],
    this.error,
  });

  const AttachmentListState.loading() : this(status: TaskDetailStatus.loading);

  const AttachmentListState.ready(List<Attachment> attachments)
      : this(status: TaskDetailStatus.ready, attachments: attachments);

  const AttachmentListState.error(OrchestratorApiException error)
      : this(status: TaskDetailStatus.error, error: error);

  final TaskDetailStatus status;
  final List<Attachment> attachments;
  final OrchestratorApiException? error;
}

/// Attachment list state holder (MT-5.7-03 entry points) — refreshes
/// live on the Section 9.6 lifecycle events while foregrounded.
class AttachmentListNotifier
    extends AutoDisposeFamilyNotifier<AttachmentListState, String> {
  StreamSubscription<OrchestratorEvent>? _eventsSub;
  bool _refetchInFlight = false;
  late String _taskId;

  @override
  AttachmentListState build(String taskId) {
    _taskId = taskId;
    final SseClient client = ref.read(sseClientProvider);
    _eventsSub = client.events.listen((OrchestratorEvent event) {
      if (!attachmentLifecycleEvents.contains(event.type) ||
          event.taskId != taskId) {
        return;
      }
      _refetch(taskId);
    });
    ref.onDispose(() {
      _eventsSub?.cancel();
      _eventsSub = null;
    });
    Future<void>.microtask(load);
    return const AttachmentListState.loading();
  }

  Future<void> load() async {
    try {
      final List<Attachment> attachments = await ref
          .read(taskDetailRepositoryProvider)
          .fetchAttachments(_taskId);
      state = AttachmentListState.ready(attachments);
    } on OrchestratorApiException catch (error) {
      state = AttachmentListState.error(error);
    }
  }

  Future<void> _refetch(String taskId) async {
    if (_refetchInFlight) {
      return;
    }
    _refetchInFlight = true;
    try {
      final List<Attachment> attachments =
          await ref.read(taskDetailRepositoryProvider).fetchAttachments(taskId);
      state = AttachmentListState.ready(attachments);
    } on OrchestratorApiException {
      // The current list stays; the next event reconciles.
    } finally {
      _refetchInFlight = false;
    }
  }
}

/// One attachment list per task id.
final AutoDisposeNotifierProviderFamily<AttachmentListNotifier,
        AttachmentListState, String> attachmentListProvider =
    AutoDisposeNotifierProviderFamily<AttachmentListNotifier,
        AttachmentListState, String>(AttachmentListNotifier.new);
