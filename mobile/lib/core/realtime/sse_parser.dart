import 'dart:convert';
import 'dart:typed_data';

/// One parsed SSE frame (Section 9.6 wire mechanics, W3C SSE shape).
///
/// * event frames carry the monotonic [id] and the envelope JSON in [data];
/// * [isHeartbeat] marks the 15 s `: heartbeat` comments — they carry no id
///   and must never move the client's resume position (Section 9.6).
class SseFrame {
  const SseFrame.event({required this.id, required this.data})
      : isHeartbeat = false;

  const SseFrame.heartbeat()
      : id = null,
        data = null,
        isHeartbeat = true;

  final int? id;
  final String? data;
  final bool isHeartbeat;
}

/// Incremental SSE parser: bytes → frames.
///
/// Follows the SSE field rules the gateway emits
/// (`backend/apps/events/fanout.py`): `id: N`, `data: {...}`, blank line
/// dispatches the frame, `:`-prefixed lines are comments (heartbeats).
/// Multi-line `data:` fields are joined with `\n` per the spec. The parser
/// never throws on malformed content — a bad frame surfaces with null
/// fields and the client skips it with a logged warning.
class SseParser {
  int? _currentId;
  final List<String> _dataLines = <String>[];
  bool _sawComment = false;

  /// Folds a byte stream into frames. UTF-8 decoding is incremental so a
  /// multi-byte character split across chunks survives.
  Stream<SseFrame> frames(Stream<Uint8List> bytes) async* {
    final Stream<String> lines = bytes
        .cast<List<int>>()
        .transform<String>(const Utf8Decoder(allowMalformed: true))
        .transform<String>(const LineSplitter());
    await for (final String line in lines) {
      final SseFrame? frame = addLine(line);
      if (frame != null) {
        yield frame;
      }
    }
  }

  /// Feeds one line; returns a frame when a blank line dispatches one.
  ///
  /// Exposed for line-level unit tests alongside the stream form.
  SseFrame? addLine(String line) {
    if (line.isEmpty) {
      final SseFrame? frame = _dispatch();
      _currentId = null;
      _dataLines.clear();
      _sawComment = false;
      return frame;
    }
    if (line.startsWith(':')) {
      // Heartbeat comment (or any comment): tolerated, state untouched.
      _sawComment = true;
      return null;
    }
    final int colon = line.indexOf(':');
    final String field = colon == -1 ? line : line.substring(0, colon);
    String value = colon == -1 ? '' : line.substring(colon + 1);
    if (value.startsWith(' ')) {
      value = value.substring(1);
    }
    switch (field) {
      case 'id':
        _currentId = int.tryParse(value);
      case 'data':
        _dataLines.add(value);
      default:
        // Named events, retry hints and unknown fields are ignored per the
        // SSE spec — not part of the Section 9.6 contract.
        break;
    }
    return null;
  }

  SseFrame? _dispatch() {
    if (_dataLines.isEmpty) {
      // Comment-only dispatch is the heartbeat; anything else is empty.
      return _sawComment ? const SseFrame.heartbeat() : null;
    }
    return SseFrame.event(
      id: _currentId,
      data: _dataLines.join('\n'),
    );
  }
}
