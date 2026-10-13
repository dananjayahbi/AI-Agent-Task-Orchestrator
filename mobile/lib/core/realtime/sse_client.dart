import 'dart:async';
import 'dart:math' as math;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../api/auth_token_interceptor.dart';
import 'event_history_source.dart';
import 'last_event_id_store.dart';
import 'orchestrator_event.dart';
import 'sse_connection_status.dart';
import 'sse_parser.dart';
import 'sse_transport.dart';

/// Reconnect backoff policy (MT-5.5-05, NFR-04): exponential growth with
/// bounded cap and jitter, plus the polling-fallback knobs.
class SseBackoffConfig {
  const SseBackoffConfig({
    this.initial = const Duration(seconds: 1),
    this.max = const Duration(seconds: 30),
    this.factor = 2.0,
    this.jitter = 0.2,
    this.maxStreamFailures = 5,
    this.pollInterval = const Duration(seconds: 15),
  })  : assert(factor >= 1),
        assert(jitter >= 0 && jitter < 1),
        assert(maxStreamFailures >= 1);

  /// Delay before the first reconnect attempt.
  final Duration initial;

  /// Upper bound on the un-jittered delay.
  final Duration max;

  /// Multiplier per consecutive failure.
  final double factor;

  /// Jitter fraction: the applied delay is
  /// `delay × (1 ± jitter×random)`.
  final double jitter;

  /// Consecutive stream failures after which the client switches to the
  /// documented polling fallback (Section 14.2, RISK-05).
  final int maxStreamFailures;

  /// Interval between history polls (and stream probes) while polling.
  final Duration pollInterval;

  /// Un-jittered delay for [attempt] (1-based): exponential, capped.
  static Duration unjitteredDelay(int attempt, SseBackoffConfig config) {
    final int exponent = math.max(0, attempt - 1);
    final double milliseconds = config.initial.inMilliseconds *
        math.pow(config.factor, exponent).toDouble();
    final int capped =
        math.min(milliseconds.round(), config.max.inMilliseconds);
    return Duration(milliseconds: capped);
  }

  /// Jittered delay for [attempt] using [random] (injectable for tests).
  static Duration delay(
      int attempt, SseBackoffConfig config, math.Random random) {
    final Duration base = unjitteredDelay(attempt, config);
    final double spread = config.jitter * (random.nextDouble() * 2 - 1);
    final double jittered = base.inMilliseconds * (1 + spread);
    return Duration(milliseconds: math.max(0, jittered.round()));
  }
}

/// The SSE resume client (MT-5.5-05; Sections 9.6, 14.2).
///
/// Contract:
/// * Connects to `GET /api/v1/events/stream` through [SseTransport] (the
///   shared Dio, so the device token is attached only while the MT-5.5-04
///   gate is unlocked — the stream never carries credentials of its own).
/// * Emits typed [OrchestratorEvent]s; malformed envelopes are skipped with
///   a logged warning and never crash the stream (acceptance item 1).
/// * **"Processed" is defined precisely:** an event is processed when it has
///   been emitted into [events]; its id is persisted only *after* that
///   emission, so a crash at worst replays the tail event on the next start
///   (at-least-once across restarts, never a gap) and the in-session
///   `id <= last` guard makes delivery exactly-once within a session
///   (acceptance item 2, the MT risk note).
/// * Reconnects send `Last-Event-ID` (SSE standard; the gateway also
///   accepts `last_event_id`) so the server replays the gap before going
///   live (Section 9.6 "no gaps, no duplicates").
/// * Heartbeat comments are tolerated and never move the resume id; a
///   stream silent for [heartbeatTimeout] (default: three missed 15 s
///   heartbeats) is treated as dead and reconnected (RISK-05).
/// * After [SseBackoffConfig.maxStreamFailures] consecutive failures the
///   client enters the documented polling fallback — `GET /events` history
///   after the last processed id, emitting the same typed events — and
///   probes the stream every poll interval until it recovers
///   (Section 14.2).
/// * [pause] disconnects cleanly; [resume] reconnects with replay
///   (foreground-only streaming, Section 14.2).
/// * A 401/AUTH_REQUIRED on the stream stops the client (the gate's
///   interceptor already discarded the credential; retrying would storm a
///   locked device — the UI returns to unlock/onboarding instead).
///
/// No token value is ever read, logged or stored here — the transport's
/// interceptors own that (Section 12.4).
class SseClient {
  SseClient({
    required SseTransport transport,
    required EventHistorySource history,
    required LastEventIdStore idStore,
    String? projectFilter,
    String? taskFilter,
    SseBackoffConfig backoff = const SseBackoffConfig(),
    Duration heartbeatTimeout = const Duration(seconds: 45),
    math.Random? random,
    void Function(String message)? onWarning,
  })  : _transport = transport,
        _history = history,
        _idStore = idStore,
        _projectFilter = projectFilter,
        _taskFilter = taskFilter,
        _backoff = backoff,
        _heartbeatTimeout = heartbeatTimeout,
        _random = random ?? math.Random(),
        _onWarning = onWarning ?? _defaultWarning;

  static const String streamPath = '/api/v1/events/stream';

  final SseTransport _transport;
  final EventHistorySource _history;
  final LastEventIdStore _idStore;
  String? _projectFilter;
  final String? _taskFilter;
  final SseBackoffConfig _backoff;
  final Duration _heartbeatTimeout;
  final math.Random _random;
  final void Function(String message) _onWarning;

  final SseParser _parser = SseParser();
  final ValueNotifier<SseConnectionStatus> _status =
      ValueNotifier<SseConnectionStatus>(SseConnectionStatus.disconnected);
  final StreamController<OrchestratorEvent> _events =
      StreamController<OrchestratorEvent>.broadcast();

  /// Last *processed* event id (see class doc for the precise definition).
  int? _lastId;
  bool _running = false;
  int _failures = 0;
  bool _filterSwitchPending = false;
  Future<void>? _loopFuture;
  SseConnection? _connection;
  Completer<void>? _pendingWait;
  Timer? _waitTimer;

  /// Connection status for UI badges (MT-5.5-05 acceptance item 5).
  ValueListenable<SseConnectionStatus> get status => _status;

  /// Typed Section 9.6 events (broadcast — subscribe before [start]).
  Stream<OrchestratorEvent> get events => _events.stream;

  /// The resume marker the client will send on the next connect, if any.
  int? get lastProcessedEventId => _lastId;

  /// The project filter the subscription currently carries (Section 9.6).
  String? get projectFilter => _projectFilter;

  /// True while the client loop is meant to be running (started, not
  /// paused/disposed).
  bool get isRunning => _running;

  /// Re-points the server-side subscription at [projectId]'s events
  /// (Section 9.6 filters; MT-5.6-04: the subscription follows the
  /// MT-5.6-02 selection).
  ///
  /// A live connection is closed so the run loop reconnects with the new
  /// filter immediately. The reconnect carries `Last-Event-ID`, so the
  /// server replays anything emitted across the switch — no gap — and the
  /// in-session id guard drops anything already processed — no duplicates
  /// (Section 9.6). The deliberate close is not counted as a stream
  /// failure.
  void updateProjectFilter(String? projectId) {
    if (projectId == _projectFilter) {
      return;
    }
    _projectFilter = projectId;
    final SseConnection? connection = _connection;
    if (_running && connection != null) {
      _filterSwitchPending = true;
      connection.close();
    }
  }

  /// Starts (or resumes) the stream after loading the persisted resume id.
  Future<void> start() async {
    if (_running) {
      return;
    }
    _lastId ??= await _idStore.read();
    // A fresh start (including app resume) gets a clean failure budget: the
    // first action is always a direct stream attempt with replay.
    _failures = 0;
    _running = true;
    _loopFuture = _runLoop();
  }

  /// App pause / gate lock: disconnects cleanly and stops the loop; the
  /// last processed id is kept for replay on [resume] (Section 14.2).
  Future<void> pause() async {
    _running = false;
    final Completer<void>? pending = _pendingWait;
    if (pending != null && !pending.isCompleted) {
      pending.complete();
    }
    _pendingWait = null;
    _waitTimer?.cancel();
    _waitTimer = null;
    _connection?.close();
    _connection = null;
    await _loopFuture;
    _loopFuture = null;
    _setStatus(SseConnectionStatus.disconnected);
  }

  /// Alias of [start] expressing the Section 14.2 app-resume lifecycle.
  Future<void> resume() => start();

  Future<void> dispose() async {
    await pause();
    await _events.close();
    _status.dispose();
  }

  Future<void> _runLoop() async {
    while (_running) {
      final bool polling = _failures >= _backoff.maxStreamFailures;
      _setStatus(polling
          ? SseConnectionStatus.polling
          : _failures == 0
              ? SseConnectionStatus.connecting
              : SseConnectionStatus.reconnecting);
      if (polling) {
        await _pollingCycle();
        continue;
      }
      try {
        await _streamSession();
        if (_filterSwitchPending) {
          // Deliberate close from [updateProjectFilter]: reconnect with the
          // new filter without spending the failure budget.
          _filterSwitchPending = false;
          continue;
        }
        // A clean server-side close still counts toward the failure budget:
        // it prevents a tight reconnect loop against a closing server.
        _failures++;
      } on DioException catch (error) {
        if (_isAuthFailure(error)) {
          _onWarning('Event stream rejected (auth) — stopping the client.');
          _running = false;
          _setStatus(SseConnectionStatus.disconnected);
          break;
        }
        _failures++;
      } catch (_) {
        // Network drop, heartbeat timeout, transport failure — reconnect.
        _failures++;
      }
      if (!_running) {
        break;
      }
      await _wait(SseBackoffConfig.delay(_failures, _backoff, _random));
    }
  }

  Future<void> _streamSession() async {
    final SseConnection connection = await _transport.open(
      path: streamPath,
      query: <String, String>{
        // `_projectFilter` is mutable (updateProjectFilter), so the field
        // does not promote — read it through a promoting local.
        if (_projectFilter != null) 'project': _projectFilter!,
        if (_taskFilter != null) 'task': _taskFilter,
      },
      headers: <String, String>{
        if (_lastId != null) 'Last-Event-ID': '$_lastId',
      },
    );
    _connection = connection;
    if (!_running) {
      // pause() landed while the connect was in flight — never leave a
      // live connection behind.
      connection.close();
      return;
    }
    _setStatus(SseConnectionStatus.connected);
    _failures = 0;
    // Heartbeat watchdog (RISK-05): a stream silent for longer than the
    // heartbeat window is treated as dead and closed, which ends this
    // session and drives a normal backoff reconnect. `Stream.timeout` is
    // not usable over the parser's async* generator, so liveness is
    // tracked explicitly; heartbeats re-arm it and never touch the resume
    // id (Section 9.6).
    Timer? watchdog;
    void armWatchdog() {
      watchdog?.cancel();
      watchdog = Timer(_heartbeatTimeout, connection.close);
    }

    armWatchdog();
    try {
      await for (final SseFrame frame in _parser.frames(connection.bytes)) {
        armWatchdog();
        if (!_running) {
          break;
        }
        if (frame.isHeartbeat) {
          // Tolerated: keeps proxies alive, carries no id, never moves the
          // resume position (Section 9.6).
          continue;
        }
        final String? data = frame.data;
        if (data == null) {
          continue;
        }
        final OrchestratorEvent? event = OrchestratorEvent.tryParseData(data);
        if (event == null) {
          _onWarning('Skipping malformed event envelope.');
          continue;
        }
        await _process(event);
      }
    } finally {
      watchdog?.cancel();
      _connection = null;
      connection.close();
    }
  }

  Future<void> _pollingCycle() async {
    try {
      final EventHistoryPage page = await _history.fetch(
        cursor:
            _lastId != null ? EventHistorySource.cursorForId(_lastId!) : null,
        project: _projectFilter,
        task: _taskFilter,
      );
      for (final OrchestratorEvent event in page.events) {
        if (!_running) {
          return;
        }
        await _process(event);
      }
    } on DioException catch (error) {
      if (_isAuthFailure(error)) {
        _running = false;
        return;
      }
      _onWarning('Event history poll failed — retrying.');
    } catch (_) {
      _onWarning('Event history poll failed — retrying.');
    }
    if (!_running) {
      return;
    }
    await _wait(_backoff.pollInterval);
    if (!_running) {
      return;
    }
    // Probe the stream: a successful open resets [_failures] inside
    // [_streamSession] and the loop returns to live mode; a failure keeps
    // the client in polling (Section 14.2 "restoring the stream when
    // possible").
    try {
      await _streamSession();
      _failures++;
    } on DioException catch (error) {
      if (_isAuthFailure(error)) {
        _running = false;
        return;
      }
      _failures++;
    } catch (_) {
      _failures++;
    }
  }

  /// One delivery step: de-duplicate, emit, then persist ("processed" =
  /// emitted — see class doc for why persistence follows emission).
  Future<void> _process(OrchestratorEvent event) async {
    if (_lastId != null && event.id <= _lastId!) {
      // Server replay overlapped what this session already processed.
      return;
    }
    _events.add(event);
    _lastId = event.id;
    try {
      await _idStore.write(event.id);
    } catch (_) {
      // Persistence failure degrades to at-most-one replay next start —
      // warn, never crash the live stream over the marker.
      _onWarning('Could not persist the last processed event id.');
    }
  }

  /// Interruptible wait so [pause] never blocks on a pending backoff.
  Future<void> _wait(Duration duration) {
    if (!_running || duration <= Duration.zero) {
      return Future<void>.value();
    }
    final Completer<void> completer = Completer<void>();
    _pendingWait = completer;
    _waitTimer = Timer(duration, () {
      if (!completer.isCompleted) {
        completer.complete();
      }
    });
    return completer.future;
  }

  void _setStatus(SseConnectionStatus value) {
    if (_status.value != value) {
      _status.value = value;
    }
  }

  /// 401-level failure — the AuthTokenInterceptor already discarded the
  /// credential when it injected the token; stop rather than storm.
  static bool _isAuthFailure(DioException error) =>
      error.response?.statusCode == 401 ||
      AuthTokenInterceptor.isAuthRequired(error);

  static void _defaultWarning(String message) {
    // Deliberately message-only: no token, header or payload content ever
    // reaches the log (Section 12.4, Section 20.4 item 3).
    debugPrint('SseClient: $message');
  }
}
