/// Connection status of the SSE client (MT-5.5-05 acceptance item 5) —
/// exposed for UI badges in later WPs (5.6–5.8).
enum SseConnectionStatus {
  /// Not started, paused, or stopped — no connection attempt in flight.
  disconnected,

  /// First connection attempt in flight.
  connecting,

  /// Stream is open and delivering (or idling between heartbeats).
  connected,

  /// The stream dropped and a bounded-backoff reconnect is scheduled or
  /// in flight (NFR-04).
  reconnecting,

  /// Repeated reconnects failed; the client is fetching event history
  /// (`GET /events`) and emitting the same typed events while it keeps
  /// probing the stream (Section 14.2 polling fallback, RISK-05).
  polling,
}
