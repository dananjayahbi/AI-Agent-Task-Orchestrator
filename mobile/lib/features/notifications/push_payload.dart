/// The Section 9.8 minimal push payload as the app receives it (MT-5.9-01;
/// the MT-5.4-02 contract it consumes).
///
/// Section 14.2: "tapping a notification deep-links to the task's review
/// sheet *after unlock*" — routing keys off the payload ids alone, so this
/// model is exactly the five-field allowlist the backend builder emits
/// (`apps/notifications/payloads.PUSH_PAYLOAD_FIELDS`): event type,
/// `project_id`, `task_id`, `task_version` and the short title, all strings
/// (FCM data maps carry strings).
///
/// **Allowlist, never blocklist** (the MT-5.4-02 risk note carried across):
/// [tryParse] *reads* only those five names — any extra key a future channel
/// might add is never looked at, so review content can never ride into
/// routing (payload minimization is a plan contract, Section 9.8). A payload
/// missing any of the five fails closed (returns null → nothing navigates):
/// the backend always sends the full set, so a partial payload is a contract
/// violation, not a degraded case to guess through.
class PushTapPayload {
  const PushTapPayload({
    required this.eventType,
    required this.projectId,
    required this.taskId,
    required this.taskVersion,
    required this.title,
  });

  /// Section 9.6-ish event type the push was dispatched for.
  final String eventType;

  /// The routing project id (validated, never sent back — Section 9.8).
  final String projectId;

  /// The task to open after unlock (the deep-link key, Section 14.2).
  final String taskId;

  /// The task state version — the MT-5.4-03 dedupe key half.
  final int taskVersion;

  /// The short banner title (a prefix of the owner's own text — MT-5.4-02).
  final String title;

  /// The MT-5.4-03 dedupe key: (event type, task id, state version).
  ///
  /// One string so the mobile-side presented-message bookkeeping (MT-5.9-02)
  /// mirrors the backend tuple without a bespoke value type.
  String get dedupeKey => '$eventType|$taskId|$taskVersion';

  /// Section 7.3 id shapes — validated client-side before any navigation
  /// (same discipline as the audit-log filter validation).
  static final RegExp projectIdShape = RegExp(r'^PID[0-9]{5}$');
  static final RegExp taskIdShape = RegExp(r'^PID[0-9]{5}-T[0-9]{3,}$');

  /// Parses the MT-5.4-02 data map; null when it is not that contract.
  ///
  /// Reads exactly the five allowlisted keys — anything else in [data] is
  /// ignored by construction. Every id is shape-checked (Section 7.3) and
  /// `task_version` must be a non-negative integer string, so a malformed or
  /// truncated message can never half-route.
  static PushTapPayload? tryParse(Map<String, String> data) {
    final String? eventType = data['event_type'];
    final String? projectId = data['project_id'];
    final String? taskId = data['task_id'];
    final String? taskVersion = data['task_version'];
    final String? title = data['title'];
    if (eventType == null ||
        eventType.isEmpty ||
        projectId == null ||
        taskId == null ||
        taskVersion == null ||
        title == null) {
      return null;
    }
    if (!projectIdShape.hasMatch(projectId) || !taskIdShape.hasMatch(taskId)) {
      return null;
    }
    final int? version = int.tryParse(taskVersion);
    if (version == null || version < 0) {
      return null;
    }
    return PushTapPayload(
      eventType: eventType,
      projectId: projectId,
      taskId: taskId,
      taskVersion: version,
      title: title,
    );
  }
}
