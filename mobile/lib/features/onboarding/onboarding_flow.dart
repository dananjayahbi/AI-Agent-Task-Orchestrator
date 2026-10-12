import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/config/app_config.dart';
import '../../core/security/auth_gate.dart';
import 'onboarding_api.dart';
import 'onboarding_messages.dart';
import 'onboarding_progress_store.dart';

/// The four Section 14.1 onboarding screens, in order.
///
/// The built-in [index] doubles as the persisted step ordinal.
enum OnboardingStep {
  serverUrl('Server URL'),
  login('Sign in'),
  deviceRegistration('Register this device'),
  biometricEnrollment('Protect the app');

  const OnboardingStep(this.title);

  final String title;

  /// Step for a persisted index, clamped into range (forward-compatible if
  /// steps are ever inserted).
  static OnboardingStep forIndex(int index) =>
      OnboardingStep.values[index.clamp(0, OnboardingStep.values.length - 1)];
}

/// Immutable view of the onboarding flow for the UI.
///
/// Deliberately contains **no token material**: the owner session token
/// lives only in the notifier's private field for the flow's duration, and
/// the device token goes straight from the API seam into the gate's secure
/// storage without touching this state (MT-5.5-06 risk note; Section 12.4).
class OnboardingState {
  const OnboardingState({
    required this.step,
    required this.serverUrl,
    this.busy = false,
    this.errorMessage,
    this.signedInAs,
    this.deviceRegistered = false,
    this.completed = false,
  });

  final OnboardingStep step;

  /// Currently entered/confirmed server URL (flavor default until edited).
  final String serverUrl;

  /// True while an async step action is in flight (disables buttons).
  final bool busy;

  /// Friendly, catalog-mapped error for the current step; null = none.
  final String? errorMessage;

  /// Username shown after login (identity, not a credential).
  final String? signedInAs;

  /// True once the device token reached secure storage via the gate.
  final bool deviceRegistered;

  /// True once the flow finished (enrollment done or honestly skipped).
  final bool completed;

  OnboardingState _copyWith({
    OnboardingStep? step,
    String? serverUrl,
    bool? busy,
    String? errorMessage,
    bool clearError = false,
    String? signedInAs,
    bool? deviceRegistered,
    bool? completed,
  }) {
    return OnboardingState(
      step: step ?? this.step,
      serverUrl: serverUrl ?? this.serverUrl,
      busy: busy ?? this.busy,
      // An explicit message wins; otherwise clearError drops the previous
      // one (used when starting a new action).
      errorMessage: errorMessage ?? (clearError ? null : this.errorMessage),
      signedInAs: signedInAs ?? this.signedInAs,
      deviceRegistered: deviceRegistered ?? this.deviceRegistered,
      completed: completed ?? this.completed,
    );
  }

  @override
  String toString() =>
      'OnboardingState($step, serverUrl: $serverUrl, busy: $busy, '
      'error: $errorMessage, signedInAs: $signedInAs, '
      'deviceRegistered: $deviceRegistered, completed: $completed)';
}

/// The flow controller (MT-5.5-06): drives the four screens in order,
/// resumable across restarts (step + URL + completion persisted, tokens
/// never — [OnboardingProgressStore]).
///
/// * **URL step** — pre-filled from flavor config; validated against the
///   server's `GET /health/live` before proceeding (Section 14.1, 9.2).
/// * **Login step** — Owner credentials via the generated client; failures
///   map catalog codes to friendly copy with no credential echo.
/// * **Registration step** — `POST /devices`; the returned device-bound
///   token is handed directly to the gate's [AuthGateNotifier.storeToken],
///   which lands the gate LOCKED pending biometrics (Section 12.2). The
///   token never appears in [OnboardingState], widgets, or logs.
/// * **Enrollment step** — guides the user to arm the biometric gate; skip
///   is honest (the app simply stays locked — no bypass claim, Section
///   14.2). Completion clears [onboardingRequiredProvider] and the gate's
///   own state performs the handoff (unlock → shell, skip → lock view).
class OnboardingFlowNotifier extends Notifier<OnboardingState> {
  /// Owner session token — in-memory only, for the flow's duration; never
  /// persisted, never logged, never in state (Section 12.4).
  String? _sessionToken;

  /// Stable idempotency key per logical registration attempt (NFR-12):
  /// regenerated only on a fresh login, so server-side dedupe holds across
  /// network retries of the same attempt.
  String? _registrationIdempotencyKey;

  int _attemptCounter = 0;

  @override
  OnboardingState build() {
    // Defensive read: consumers (the lock gate) may construct this flow in
    // environments without dart-define configuration (widget tests).
    String configUrl = '';
    try {
      configUrl = ref.read(appConfigProvider).apiBaseUrl;
    } catch (_) {
      // No resolved config — the URL step simply starts empty.
    }
    // Restore is async; start from the flavor default and reconcile in a
    // microtask (same pattern as the gate's cold-start probe).
    Future<void>.microtask(_restore);
    return OnboardingState(
      step: OnboardingStep.serverUrl,
      serverUrl: configUrl,
    );
  }

  /// Restores the persisted step. Tokens do not survive restarts, so
  /// resume is honest about what still needs an API call:
  /// * URL step persisted → back to it (nothing done yet).
  /// * login/registration step → login (the owner session was in memory).
  /// * enrollment step → straight to it: the device token was already
  ///   stored (the step only advances after [storeToken] succeeded), so no
  ///   credential is needed to finish arming the gate.
  /// * completed → login step (post-revocation re-entry re-authenticates;
  ///   a locked app with a stored token never shows onboarding anyway).
  Future<void> _restore() async {
    try {
      final OnboardingProgressStore store =
          ref.read(onboardingProgressStoreProvider);
      final String? savedUrl = await store.readServerUrl();
      final int? savedStep = await store.readStep();
      final bool completed = await store.readCompleted();
      if (savedStep == null && savedUrl == null && !completed) {
        return; // Fresh install — start at the URL step.
      }
      final OnboardingStep restored = OnboardingStep.forIndex(savedStep ?? 0);
      final OnboardingStep resumed;
      if (completed ||
          restored == OnboardingStep.login ||
          restored == OnboardingStep.deviceRegistration) {
        resumed = OnboardingStep.login;
      } else {
        resumed = restored; // serverUrl or biometricEnrollment
      }
      state = state._copyWith(
        step: resumed,
        serverUrl: savedUrl ?? state.serverUrl,
        completed: completed,
        deviceRegistered: restored == OnboardingStep.biometricEnrollment,
      );
    } catch (_) {
      // Progress store unreadable: start fresh rather than block setup.
    }
  }

  /// Validates the entered URL against the server's health endpoint and,
  /// on success, persists it (overriding the flavor default — app_config
  /// precedence decision) and advances to login.
  Future<void> confirmServerUrl(String url) async {
    final String trimmed = url.trim();
    if (trimmed.isEmpty) {
      state = state._copyWith(
        clearError: true,
        errorMessage: 'Enter the server address.',
      );
      return;
    }
    final Uri? parsed = Uri.tryParse(trimmed);
    if (parsed == null ||
        !(parsed.isScheme('http') || parsed.isScheme('https')) ||
        parsed.host.isEmpty) {
      state = state._copyWith(
        clearError: true,
        errorMessage: 'Enter a full address like http://10.0.2.2:8000/api/v1.',
      );
      return;
    }
    state = state._copyWith(busy: true, clearError: true, serverUrl: trimmed);
    try {
      await ref.read(onboardingApiProvider).checkServerReachable(trimmed);
      await ref.read(onboardingProgressStoreProvider).writeServerUrl(trimmed);
      state = state._copyWith(
        busy: false,
        step: OnboardingStep.login,
        clearError: true,
      );
      await _persistStep(OnboardingStep.login);
    } on OrchestratorApiException catch (error) {
      state = state._copyWith(
        busy: false,
        errorMessage: friendlyOnboardingMessage(error),
      );
    } catch (_) {
      state = state._copyWith(
        busy: false,
        errorMessage:
            'Could not reach the server — check the address and your connection.',
      );
    }
  }

  /// Owner login via `POST /auth/login`. The password and the returned
  /// session token never enter state (Section 12.4).
  Future<void> login({
    required String username,
    required String password,
  }) async {
    if (username.trim().isEmpty || password.isEmpty) {
      state = state._copyWith(
        clearError: true,
        errorMessage: 'Enter your username and password.',
      );
      return;
    }
    state = state._copyWith(busy: true, clearError: true);
    try {
      final OwnerLoginResult result =
          await ref.read(onboardingApiProvider).login(
                baseUrl: state.serverUrl,
                username: username.trim(),
                password: password,
              );
      _sessionToken = result.sessionToken;
      // A new login starts a new logical registration attempt.
      _registrationIdempotencyKey = null;
      state = state._copyWith(
        busy: false,
        step: OnboardingStep.deviceRegistration,
        signedInAs: result.username,
        clearError: true,
      );
      await _persistStep(OnboardingStep.deviceRegistration);
    } on OrchestratorApiException catch (error) {
      state = state._copyWith(
        busy: false,
        errorMessage: friendlyOnboardingMessage(error),
      );
    } catch (_) {
      state = state._copyWith(
        busy: false,
        errorMessage:
            'Could not reach the server — check the address and your connection.',
      );
    }
  }

  /// Registers this device and hands the device-bound token straight to
  /// the gate's secure storage (MT-5.5-04). The token is passed as a
  /// parameter through this single call and nowhere else.
  Future<void> registerDevice() async {
    final String? sessionToken = _sessionToken;
    if (sessionToken == null) {
      // Session lost (restart mid-flow or revocation): go back to login
      // honestly rather than pretending.
      state = state._copyWith(
        step: OnboardingStep.login,
        clearError: true,
        errorMessage: 'Please sign in again to continue.',
      );
      return;
    }
    state = state._copyWith(busy: true, clearError: true);
    _attemptCounter += 1;
    _registrationIdempotencyKey ??= 'onboarding-device-$_attemptCounter';
    try {
      final String deviceToken =
          await ref.read(onboardingApiProvider).registerDevice(
                baseUrl: state.serverUrl,
                ownerSessionToken: sessionToken,
                idempotencyKey: _registrationIdempotencyKey!,
              );
      // Handoff point (review line by line — MT risk note): response token
      // → gate storage, in one call; no intermediate state, no logging.
      await ref.read(authGateProvider.notifier).storeToken(deviceToken);
      // The owner session has done its job; drop it from memory too.
      _sessionToken = null;
      state = state._copyWith(
        busy: false,
        deviceRegistered: true,
        step: OnboardingStep.biometricEnrollment,
        clearError: true,
      );
      await _persistStep(OnboardingStep.biometricEnrollment);
    } on OrchestratorApiException catch (error) {
      state = state._copyWith(
        busy: false,
        errorMessage: friendlyOnboardingMessage(error),
      );
    } catch (_) {
      state = state._copyWith(
        busy: false,
        errorMessage: 'Device registration failed — try again.',
      );
    }
  }

  /// Completes onboarding (enrollment done or skipped) and hands off to
  /// the gate: with the flag cleared, the lock gate renders whatever the
  /// gate state says — the shell once unlocked, the lock view while still
  /// locked. Skipping is honest: no enrollment is claimed that did not
  /// happen (Section 14.2).
  Future<void> finish() async {
    try {
      await ref.read(onboardingProgressStoreProvider).writeCompleted(true);
    } catch (_) {
      // Losing the resume marker only means a future fresh install starts
      // over — not worth failing the handoff.
    }
    state = state._copyWith(completed: true, clearError: true, busy: false);
    ref.read(onboardingRequiredProvider.notifier).state = false;
  }

  /// Back from the login step to the URL step (resumable navigation).
  void backToServerUrl() {
    if (state.step == OnboardingStep.login) {
      state = state._copyWith(step: OnboardingStep.serverUrl, clearError: true);
    }
  }

  /// The stored device credential was rejected and discarded (401
  /// AUTH_REQUIRED, release contract): re-enter onboarding at login — the
  /// user registers a fresh device credential. In-memory session is gone.
  void notifyCredentialRejected() {
    _sessionToken = null;
    _registrationIdempotencyKey = null;
    state = state._copyWith(
      step: OnboardingStep.login,
      completed: false,
      deviceRegistered: false,
      clearError: true,
    );
  }

  Future<void> _persistStep(OnboardingStep step) async {
    try {
      await ref.read(onboardingProgressStoreProvider).writeStep(step.index);
    } catch (_) {
      // Non-fatal: worst case a restart resumes one step earlier.
    }
  }
}

/// The single source of onboarding flow state (Section 14.3).
final NotifierProvider<OnboardingFlowNotifier, OnboardingState>
    onboardingFlowProvider =
    NotifierProvider<OnboardingFlowNotifier, OnboardingState>(
  OnboardingFlowNotifier.new,
);
