import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/features/task_detail/attachment_list_section.dart';
import 'package:orchestrator_mobile/features/task_detail/attachment_viewer_screen.dart';
import 'package:orchestrator_mobile/features/task_detail/untrusted_content_banner.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart'
    hide DashboardSummary, ProjectDashboardCard;

import '../realtime/realtime_test_support.dart';
import 'task_detail_test_support.dart';

/// MT-5.7-03 battery: attachment viewing — image + tabs, OCR content,
/// document pagination (Section 9.5), processing/failed statuses
/// (Section 7.2), the untrusted-content banner on text outputs (P10),
/// both catalog error paths, and the OQ-07 description hiding.
void main() {
  late FakeAttachmentRepository repository;
  late FakeTaskDetailRepository taskRepository;
  late FakeSseTransport transport;
  late SseClient client;

  setUp(() {
    repository = FakeAttachmentRepository();
    taskRepository = FakeTaskDetailRepository();
    transport = FakeSseTransport();
    client = buildDetailTestSseClient(transport: transport);
  });

  Future<void> pumpViewer(
    WidgetTester tester,
    Attachment attachment, {
    String? taskId = 'PID00001-T1',
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: taskDetailOverrides(
          repository: taskRepository,
          attachments: repository,
          sseClient: client,
        ),
        child: MaterialApp(
          home: AttachmentViewerScreen(attachment: attachment),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  group('image viewing (acceptance item 1)', () {
    testWidgets(
        'image_base64 content renders through the auth-aware '
        'client with pinch-zoom; OCR tab loads text_ocr',
        (WidgetTester tester) async {
      // A 1×1 transparent PNG (shared fixture in test support).
      final Attachment image = makeAttachment(id: 'A1', isImage: true);
      repository
        ..rows['A1'] = image
        ..content['A1|image_base64'] = makeContent(
          attachmentId: 'A1',
          format: 'image_base64',
          imageBase64: validPngBase64,
        )
        ..content['A1|text_ocr'] = makeContent(
          attachmentId: 'A1',
          format: 'text_ocr',
          content: '⚠ Untrusted: some extracted words',
          description: 'a red button at the top',
        );
      await pumpViewer(tester, image);

      // Image tab shows the decoded bytes inside an InteractiveViewer.
      expect(find.byKey(const ValueKey<String>('attachment-image-pane')),
          findsOneWidget);
      expect(find.byKey(const ValueKey<String>('attachment-image')),
          findsOneWidget);
      // The explicit format was requested — never `auto` guessing.
      expect(repository.contentCalls.first['format'], 'image_base64');

      // OCR tab: transcript + layout description, bannered (P10).
      await tester.tap(find.text('OCR'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('attachment-ocr-text')),
        findsOneWidget,
      );
      expect(find.textContaining('some extracted words'), findsOneWidget);
      expect(find.textContaining('a red button at the top'), findsOneWidget);
      expect(
        find.byKey(const ValueKey<String>('untrusted-content-banner')),
        findsOneWidget,
      );
      // The server's own banner prefix was not stripped.
      expect(find.textContaining('⚠ Untrusted'), findsOneWidget);
      expect(repository.contentCalls.last['format'], 'text_ocr');
    });

    testWidgets(
        'the description pane hides gracefully when the '
        'description provider is disabled (OQ-07 default)',
        (WidgetTester tester) async {
      final Attachment image = makeAttachment(
        id: 'A1',
        isImage: true,
        shortDescription: null,
      );
      repository
        ..rows['A1'] = image
        ..content['A1|image_base64'] = makeContent(
          attachmentId: 'A1',
          format: 'image_base64',
          imageBase64: validPngBase64,
        );
      await pumpViewer(tester, image);

      expect(find.text('Description'), findsNothing);

      // With a description present, the pane appears.
      final Attachment described = makeAttachment(
        id: 'A2',
        isImage: true,
        shortDescription: 'A screenshot of the settings screen.',
      );
      repository
        ..rows['A2'] = described
        ..content['A2|image_base64'] = makeContent(
          attachmentId: 'A2',
          format: 'image_base64',
          imageBase64: validPngBase64,
        );
      await pumpViewer(tester, described);
      expect(find.text('Description'), findsOneWidget);
      await tester.tap(find.text('Description'));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('attachment-description-text')),
        findsOneWidget,
      );
      expect(
        find.text('A screenshot of the settings screen.'),
        findsOneWidget,
      );
    });
  });

  group('document pagination (acceptance item 2; Section 9.5)', () {
    testWidgets(
        'pages navigate with page_number/total_pages honored and '
        'one page per call', (WidgetTester tester) async {
      final Attachment doc = makeAttachment(
        id: 'D1',
        filename: 'spec.md',
        mimeType: 'text/markdown',
        isImage: false,
      );
      repository
        ..rows['D1'] = doc
        ..content['D1|markdown|1'] = makeContent(
          attachmentId: 'D1',
          format: 'markdown',
          content: 'Page one body',
          pageNumber: 1,
          totalPages: 3,
          tokenCount: 120,
        )
        ..content['D1|markdown|2'] = makeContent(
          attachmentId: 'D1',
          format: 'markdown',
          content: 'Page two body',
          pageNumber: 2,
          totalPages: 3,
          tokenCount: 90,
        );
      await pumpViewer(tester, doc);

      expect(
        find.byKey(const ValueKey<String>('attachment-page-indicator')),
        findsOneWidget,
      );
      expect(find.text('Page 1 of 3 · ~120 tokens'), findsOneWidget);
      expect(find.text('Page one body'), findsOneWidget);
      // The untrusted banner is present on the text-derived pane.
      expect(
        find.byKey(const ValueKey<String>('untrusted-content-banner')),
        findsOneWidget,
      );

      // Next: exactly one page-two call, no prefetch beyond the visible.
      await tester
          .tap(find.byKey(const ValueKey<String>('attachment-page-next')));
      await tester.pumpAndSettle();
      expect(find.text('Page 2 of 3 · ~90 tokens'), findsOneWidget);
      expect(find.text('Page two body'), findsOneWidget);
      final List<Map<String, Object?>> markdownCalls = repository.contentCalls
          .where((Map<String, Object?> c) => c['format'] == 'markdown')
          .toList();
      expect(markdownCalls, hasLength(2),
          reason: 'one page per call — no hidden prefetch (RISK-13)');

      // Prev back to page one.
      await tester
          .tap(find.byKey(const ValueKey<String>('attachment-page-prev')));
      await tester.pumpAndSettle();
      expect(find.text('Page 1 of 3 · ~120 tokens'), findsOneWidget);

      // At page one the prev button is disabled.
      final Finder prev =
          find.byKey(const ValueKey<String>('attachment-page-prev'));
      expect(tester.widget<IconButton>(prev).onPressed, isNull);
    });
  });

  group('processing lifecycle (acceptance item 4; Section 7.2)', () {
    testWidgets(
        'processing status shows and flips to ready on the '
        'attachment.ready event (foreground live refresh)',
        (WidgetTester tester) async {
      final Attachment processing = makeAttachment(
        id: 'A1',
        processingStatus: 'processing',
      );
      repository.rows['A1'] = processing;
      await pumpViewer(tester, processing);

      expect(
        find.byKey(const ValueKey<String>('attachment-viewer-processing')),
        findsOneWidget,
      );

      // The pipeline finishes; the Section 9.6 event arrives.
      repository
        ..rows['A1'] = makeAttachment(id: 'A1', processingStatus: 'ready')
        ..content['A1|image_base64'] = makeContent(
          attachmentId: 'A1',
          format: 'image_base64',
          imageBase64: validPngBase64,
        );
      transport.queueStream();
      await client.start();
      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          type: 'attachment.ready',
          taskId: 'PID00001-T1',
          data: <String, dynamic>{'attachment_id': 'A1'},
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey<String>('attachment-image-pane')),
        findsOneWidget,
        reason: 'the ready transition loads and shows the image',
      );

      await client.dispose();
    });

    testWidgets('failed status shows the failure detail (Section 7.2)',
        (WidgetTester tester) async {
      final Attachment failed = makeAttachment(
        id: 'A1',
        processingStatus: 'failed',
        failureReason: 'OCR engine timed out.',
      );
      repository.rows['A1'] = failed;
      await pumpViewer(tester, failed);

      expect(
        find.byKey(const ValueKey<String>('attachment-viewer-failed')),
        findsOneWidget,
      );
      expect(find.text('OCR engine timed out.'), findsOneWidget);
    });
  });

  group('catalog error paths (acceptance item 4; Section 20.4 item 5)', () {
    testWidgets(
        'ATTACHMENT_NOT_READY maps to the friendly processing '
        'state, never raw server text', (WidgetTester tester) async {
      final Attachment image = makeAttachment(id: 'A1');
      repository
        ..rows['A1'] = image
        ..nextContentErrors['A1|image_base64'] = apiError(
          CodeEnum.ATTACHMENT_NOT_READY,
          statusCode: 409,
        );
      await pumpViewer(tester, image);

      expect(
        find.byKey(const ValueKey<String>('attachment-content-error')),
        findsOneWidget,
      );
      expect(
        find.textContaining('still being processed'),
        findsOneWidget,
      );
      expect(find.text('scripted'), findsNothing,
          reason: 'the raw server message never reaches the UI');
    });

    testWidgets(
        'ATTACHMENT_UNSUPPORTED_FORMAT maps to the friendly '
        'unsupported state', (WidgetTester tester) async {
      final Attachment doc = makeAttachment(
        id: 'D1',
        isImage: false,
        filename: 'weird.bin',
        mimeType: 'application/octet-stream',
      );
      repository
        ..rows['D1'] = doc
        ..nextContentErrors['D1|markdown'] = apiError(
          CodeEnum.ATTACHMENT_UNSUPPORTED_FORMAT,
          statusCode: 415,
        );
      await pumpViewer(tester, doc);

      expect(
        find.byKey(const ValueKey<String>('attachment-content-error')),
        findsOneWidget,
      );
      expect(
        find.textContaining('cannot be displayed'),
        findsOneWidget,
      );
    });

    testWidgets(
        'a row-level 404 shows the full error state with catalog '
        'copy', (WidgetTester tester) async {
      repository.nextRowError =
          apiError(CodeEnum.ATTACHMENT_NOT_READY, statusCode: 409);
      await pumpViewer(tester, makeAttachment(id: 'A1'));

      expect(
        find.byKey(const ValueKey<String>('attachment-viewer-error')),
        findsOneWidget,
      );
      expect(find.text('scripted'), findsNothing);
    });
  });

  group('attachment list entry points (acceptance item 1)', () {
    testWidgets('list shows processing badges and opens the viewer',
        (WidgetTester tester) async {
      taskRepository.attachments['PID00001-T1'] = <Attachment>[
        makeAttachment(
          id: 'A1',
          filename: 'ready.png',
          processingStatus: 'ready',
        ),
        makeAttachment(
          id: 'A2',
          filename: 'pending.pdf',
          mimeType: 'application/pdf',
          isImage: false,
          processingStatus: 'processing',
        ),
      ];
      repository
        ..rows['A1'] = makeAttachment(id: 'A1', filename: 'ready.png')
        ..content['A1|image_base64'] = makeContent(
          attachmentId: 'A1',
          format: 'image_base64',
          imageBase64: validPngBase64,
        );
      await tester.pumpWidget(
        ProviderScope(
          overrides: taskDetailOverrides(
            repository: taskRepository,
            attachments: repository,
            sseClient: client,
          ),
          child: MaterialApp(
            home: Scaffold(
              body: ListView(
                children: const <Widget>[
                  SizedBox(
                    height: 400,
                    child: AttachmentListSection(taskId: 'PID00001-T1'),
                  ),
                ],
              ),
            ),
            routes: <String, WidgetBuilder>{
              '/attachment-viewer': (BuildContext context) =>
                  AttachmentViewerScreen(
                    attachment: ModalRoute.of(context)!.settings.arguments
                        as Attachment,
                  ),
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey<String>('attachment-status-A1')),
        findsOneWidget,
      );
      expect(find.textContaining('Ready'), findsOneWidget);
      expect(find.textContaining('Processing'), findsOneWidget);

      await tester.tap(
        find.byKey(const ValueKey<String>('attachment-tile-A1')),
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey<String>('attachment-image-pane')),
          findsOneWidget,
          reason: 'the tile opens the viewer for that attachment');
    });

    testWidgets('the section refreshes its list on a lifecycle event',
        (WidgetTester tester) async {
      taskRepository.attachments['PID00001-T1'] = <Attachment>[
        makeAttachment(id: 'A1'),
      ];
      await tester.pumpWidget(
        ProviderScope(
          overrides: taskDetailOverrides(
            repository: taskRepository,
            attachments: repository,
            sseClient: client,
          ),
          child: const MaterialApp(
            home: Scaffold(
              body: SizedBox(
                height: 400,
                child: AttachmentListSection(taskId: 'PID00001-T1'),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey<String>('attachment-tile-A1')),
        findsOneWidget,
      );

      // A new upload lands and the pipeline emits; the list refetches.
      taskRepository.attachments['PID00001-T1'] = <Attachment>[
        makeAttachment(id: 'A1'),
        makeAttachment(id: 'A2', filename: 'second.png'),
      ];
      transport.queueStream();
      await client.start();
      transport.emitTo(
        0,
        envelopeJson(
          id: 1,
          type: 'attachment.processing',
          taskId: 'PID00001-T1',
          data: <String, dynamic>{'attachment_id': 'A2'},
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey<String>('attachment-tile-A2')),
        findsOneWidget,
        reason: 'the lifecycle event refreshes the entry list',
      );

      await client.dispose();
    });
  });

  group('P10 banner (acceptance item 3)', () {
    testWidgets('the banner widget renders the untrusted-content message',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: UntrustedContentBanner())),
      );
      expect(
        find.byKey(const ValueKey<String>('untrusted-content-banner')),
        findsOneWidget,
      );
      expect(find.textContaining('Untrusted content'), findsOneWidget);
    });
  });
}
