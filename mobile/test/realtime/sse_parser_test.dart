import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:orchestrator_mobile/core/realtime/sse_parser.dart';

void main() {
  SseParser newParser() => SseParser();

  Stream<Uint8List> bytesOf(List<String> chunks) =>
      Stream<Uint8List>.fromIterable(
        chunks.map((String c) => Uint8List.fromList(utf8.encode(c))),
      );

  group('SseParser', () {
    test('parses an id/data frame per the gateway wire format', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>['id: 7\ndata: {"a":1}\n\n']))
          .toList();
      expect(frames, hasLength(1));
      expect(frames.single.id, 7);
      expect(frames.single.data, '{"a":1}');
      expect(frames.single.isHeartbeat, isFalse);
    });

    test('tolerates heartbeat comments without producing event frames',
        () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>[
            ': heartbeat\n\n',
            'id: 8\ndata: {}\n\n',
            ': heartbeat\n\n',
          ]))
          .toList();
      expect(frames, hasLength(3));
      expect(frames[0].isHeartbeat, isTrue);
      expect(frames[0].id, isNull);
      expect(frames[1].isHeartbeat, isFalse);
      expect(frames[1].id, 8);
      expect(frames[2].isHeartbeat, isTrue);
    });

    test('handles frames split across arbitrary byte chunks', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>[
            'id: ',
            '9',
            '\ndata: {"x"',
            ': "y"}',
            '\n',
            '\n',
          ]))
          .toList();
      expect(frames, hasLength(1));
      expect(frames.single.id, 9);
      // The two chunks concatenate mid-line, so the JSON keeps its space.
      expect(frames.single.data, '{"x": "y"}');
    });

    test('survives a multi-byte UTF-8 character split across chunks', () async {
      final List<int> euro = utf8.encode('{"n":"€"}');
      final Stream<Uint8List> stream =
          Stream<Uint8List>.fromIterable(<Uint8List>[
        Uint8List.fromList(<int>[
          ...utf8.encode('id: 1\ndata: '),
          ...euro.sublist(0, euro.length - 1)
        ]),
        Uint8List.fromList(<int>[euro.last, ...utf8.encode('\n\n')]),
      ]);
      final List<SseFrame> frames = await newParser().frames(stream).toList();
      expect(frames, hasLength(1));
      expect(frames.single.data, '{"n":"€"}');
    });

    test('joins multi-line data fields with a newline (SSE spec)', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>['id: 2\ndata: line1\ndata: line2\n\n']))
          .toList();
      expect(frames.single.data, 'line1\nline2');
    });

    test('a blank line with no pending frame yields nothing', () async {
      final SseParser parser = newParser();
      expect(parser.addLine(''), isNull);
      expect(parser.addLine(': heartbeat'), isNull);
      expect(
          parser.addLine(''), isNotNull); // comment-only dispatch = heartbeat
    });

    test('unknown fields and retry hints are ignored', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>[
            'event: message\nretry: 5000\nunknown: x\nid: 3\ndata: {}\n\n',
          ]))
          .toList();
      expect(frames, hasLength(1));
      expect(frames.single.id, 3);
      expect(frames.single.data, '{}');
    });

    test('id reset: a later frame without an id carries null', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>[
            'id: 4\ndata: {}\n\ndata: {}\n\n',
          ]))
          .toList();
      expect(frames, hasLength(2));
      expect(frames[0].id, 4);
      expect(frames[1].id, isNull);
    });

    test('non-numeric id is ignored but the frame still dispatches', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>['id: abc\ndata: {}\n\n']))
          .toList();
      expect(frames.single.id, isNull);
      expect(frames.single.data, '{}');
    });

    test('CRLF line endings are handled', () async {
      final List<SseFrame> frames = await newParser()
          .frames(bytesOf(<String>['id: 5\r\ndata: {}\r\n\r\n']))
          .toList();
      expect(frames.single.id, 5);
      expect(frames.single.data, '{}');
    });
  });
}
