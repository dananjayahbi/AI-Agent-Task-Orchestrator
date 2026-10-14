import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

/// Raised when the platform cannot run speech-to-text right now —
/// capability missing, the OS does not offer recognition, or the
/// microphone permission is denied/unavailable (MT-5.8-05 risk note:
/// surface as "dictation unavailable", never a crash).
class DictationUnavailableException implements Exception {
  const DictationUnavailableException(this.reason);

  /// Short, non-technical cause: `permission` or `capability`.
  final String reason;

  @override
  String toString() => 'DictationUnavailableException($reason)';
}

/// On-device dictation seam for the request-changes note (Section 14.2
/// voice-note rules) — one abstraction so widget tests script a session
/// while production uses the OS speech framework.
///
/// Contract: **text only**. Implementations never upload audio
/// themselves; the OS recognizer owns capture (Section 14.2: on-device
/// speech-to-text, no third-party service, no audio upload in v1).
abstract class DictationService {
  /// Begins a dictation session; resolves once listening has started.
  ///
  /// [onText] receives the running transcript (committed text plus the
  /// current partial) after every result; [onEnded] fires when the
  /// session stops on its own (platform timeout / final result).
  /// Throws [DictationUnavailableException] when dictation cannot run.
  Future<void> start({
    required void Function(String text) onText,
    required void Function() onEnded,
  });

  /// Ends an active session (keeps the transcript the caller already
  /// received); a no-op when nothing is listening.
  Future<void> stop();
}

/// Production implementation over the OS speech framework
/// (`speech_to_text`): `onDevice: true` asks for recognition that
/// never leaves the device where the platform supports it; where the
/// platform cannot deliver, the listen session fails and the caller
/// degrades to typed input (RISK-09: dictation is an enhancement —
/// the required text input always works).
class SpeechDictationService implements DictationService {
  SpeechDictationService({SpeechToText? speech})
      : _speech = speech ?? SpeechToText();

  final SpeechToText _speech;
  bool _initialized = false;
  void Function()? _onEnded;
  String _committed = '';
  bool _sessionActive = false;

  @override
  Future<void> start({
    required void Function(String text) onText,
    required void Function() onEnded,
  }) async {
    if (_sessionActive) {
      await stop();
    }
    _onEnded = onEnded;
    _committed = '';

    if (!_initialized) {
      // initialize() also prompts for the microphone permission on the
      // platforms that prompt; false means denied or unavailable.
      final bool ok = await _speech.initialize(
        onError: (error) => _finishSession(),
        onStatus: (status) {
          if (status == 'done' || status == 'notListening') {
            _finishSession();
          }
        },
      );
      if (!ok) {
        throw const DictationUnavailableException('permission');
      }
      _initialized = true;
    }

    try {
      _sessionActive = true;
      await _speech.listen(
        listenOptions: SpeechListenOptions(
          partialResults: true,
          onDevice: true,
          listenFor: const Duration(seconds: 30),
          pauseFor: const Duration(seconds: 6),
          cancelOnError: true,
        ),
        onResult: (SpeechRecognitionResult result) {
          final String text = result.recognizedWords.trim();
          if (result.finalResult) {
            _committed = _committed.isEmpty
                ? text
                : (_committed.endsWith(text)
                    ? _committed
                    : '$_committed $text');
          }
          final String display = result.finalResult || text.isEmpty
              ? _committed
              : (_committed.isEmpty ? text : '$_committed $text');
          onText(display);
        },
      );
    } on DictationUnavailableException {
      _sessionActive = false;
      rethrow;
    } catch (_) {
      // Any platform failure (unsupported, refused, not initialized)
      // is an unavailable-capability outcome — never a crash.
      _sessionActive = false;
      throw const DictationUnavailableException('capability');
    }
  }

  @override
  Future<void> stop() async {
    if (!_sessionActive) {
      return;
    }
    try {
      await _speech.stop();
    } catch (_) {
      // Session already ended at the platform — the caller's text is
      // intact either way.
    }
    _finishSession();
  }

  void _finishSession() {
    if (!_sessionActive) {
      return;
    }
    _sessionActive = false;
    final void Function()? ended = _onEnded;
    _onEnded = null;
    ended?.call();
  }
}

/// The app-wide dictation seam; tests override it with a scripted
/// implementation.
final Provider<DictationService> dictationServiceProvider =
    Provider<DictationService>(
  (Ref ref) => SpeechDictationService(),
);
