import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'biometric_authenticator.dart';
import 'secure_token_store.dart';

/// Where the gate stands (parent plan Section 14.2, FR-MOB-06).
enum GateStatus {
  /// Cold start: probing secure storage before anything is released.
  initializing,

  /// No device credential is stored — the app has no secret to guard and
  /// routes to onboarding (MT-5.5-06) for registration.
  noCredential,

  /// A credential exists but is not released: biometric (or OS passcode
  /// fallback) success is required first.
  locked,

  /// Biometric success happened; the token may be released to authenticated
  /// requests until the inactivity timeout re-locks.
  unlocked,

  /// Secure storage could not be read — the lock view says so and offers a
  /// retry; never a silent bypass (Section 14.2 honest states).
  storageError,
}

/// Immutable view of the gate for the UI layer.
class AuthGateState {
  const AuthGateState({
    required this.status,
    this.availability = BiometricAvailability.unknown,
    this.lastUnlockFailed = false,
  });

  final GateStatus status;

  /// Probed OS-authentication capability (drives the lock view's messaging).
  final BiometricAvailability availability;

  /// True when the most recent unlock attempt was rejected — the lock view
  /// shows an honest "not recognized" hint (no secrets involved).
  final bool lastUnlockFailed;

  @override
  String toString() =>
      'AuthGateState($status, $availability, unlockFailed: $lastUnlockFailed)';
}

/// The inactivity timeout before the token is re-locked (Section 14.2:
/// "configurable inactivity timeout"). **WP-5.5 decision:** the plan leaves
/// the value unspecified; the documented default is **5 minutes** of no user
/// activity, overridable per environment later if the owner wants tighter
/// policy (Section 9.10 discipline: every setting has a documented default).
final Provider<Duration> lockTimeoutProvider = Provider<Duration>(
  (Ref ref) => const Duration(minutes: 5),
);

/// True while the app must render the onboarding flow instead of the shell
/// or the lock view (MT-5.5-06; Section 14.1).
///
/// Three situations set it: a fresh install (seeded by `main()` from the
/// persisted onboarding progress), a mid-flow resume, and post-revocation
/// re-entry ([AuthGateNotifier.discardCredential], release contract —
/// rejection returns the app to onboarding). [OnboardingFlowNotifier]
/// clears it when onboarding completes.
///
/// The default is `false` so consumers built before `main()`'s seed (and
/// tests that never run onboarding) see the plain gate behavior.
final StateProvider<bool> onboardingRequiredProvider = StateProvider<bool>(
  (Ref ref) => false,
);

/// The biometric gate (MT-5.5-04; ADR-006 layer 3).
///
/// * The device token lives in platform secure storage and is **released to
///   outbound requests only after biometric success** (Section 12.2,
///   Section 14.2). Cold start always begins locked.
/// * A configurable inactivity timeout re-locks; [lock] also stops releasing
///   immediately (background timeout, MT scope).
/// * Devices without enrolled biometrics get explicit enrollment guidance —
///   the gate never bypasses itself (Section 14.2 honest states).
/// * The token value is never logged, never placed in [AuthGateState], and
///   exists in memory only between unlock and re-lock
///   (docs/mobile/device-auth-release-contract.md).
class AuthGateNotifier extends Notifier<AuthGateState> {
  Timer? _inactivityTimer;
  String? _releasedToken;
  Future<void> _initialized = Future<void>.value();

  /// Completes when the cold-start storage probe has finished (tests and the
  /// lock view await it; the UI shows a loading state until then).
  Future<void> get initialized => _initialized;

  @override
  AuthGateState build() {
    ref.onDispose(() => _inactivityTimer?.cancel());
    // Kick off the cold-start probe after build returns (a microtask, so a
    // synchronously-failing store cannot have its state assignment
    // overwritten by build's return); the UI shows the honest
    // "initializing" state until it completes.
    _initialized = Future<void>.microtask(_initialize);
    return const AuthGateState(status: GateStatus.initializing);
  }

  /// Cold start: a stored credential means the app opens LOCKED — biometric
  /// success is required before the token is released (Section 14.2).
  Future<void> _initialize() async {
    try {
      final String? token =
          await ref.read(secureTokenStoreProvider).read(deviceTokenStorageKey);
      if (token == null || token.isEmpty) {
        state = const AuthGateState(status: GateStatus.noCredential);
        return;
      }
      state = AuthGateState(
        status: GateStatus.locked,
        availability: await ref.read(biometricAuthProvider).availability(),
      );
    } catch (_) {
      // Honest failure: storage unreadable means we cannot prove a
      // credential exists — say so, offer retry, never unlock.
      state = const AuthGateState(status: GateStatus.storageError);
    }
  }

  /// Prompts for biometric (or OS passcode fallback) success. Returns true
  /// only when the token was released. On devices without enrolled
  /// biometrics the prompt may still offer the passcode fallback — but a
  /// failed or unavailable prompt leaves the gate locked with enrollment
  /// guidance, never a bypass (Section 14.2).
  Future<bool> unlock() async {
    if (state.status == GateStatus.noCredential ||
        state.status == GateStatus.storageError) {
      return false;
    }
    final BiometricAuthenticator authenticator =
        ref.read(biometricAuthProvider);
    if (state.availability == BiometricAvailability.unsupported) {
      // No OS authentication exists on this device — documented limitation;
      // do not pretend to unlock.
      return false;
    }

    final bool success =
        await authenticator.authenticate(reason: 'Unlock the Orchestrator');
    if (!success) {
      state = AuthGateState(
        status: GateStatus.locked,
        availability: state.availability,
        lastUnlockFailed: true,
      );
      return false;
    }

    final String? token =
        await ref.read(secureTokenStoreProvider).read(deviceTokenStorageKey);
    if (token == null || token.isEmpty) {
      // Raced with a discard (e.g. server-side revocation): stay honest.
      state = const AuthGateState(status: GateStatus.noCredential);
      return false;
    }
    _releasedToken = token;
    state = AuthGateState(
      status: GateStatus.unlocked,
      availability: state.availability,
    );
    _restartInactivityTimer();
    return true;
  }

  /// Hands the token to the authenticated request layer — and only that
  /// layer — when (and only when) the gate is unlocked. Returns null while
  /// locked, so a locked app sends no Authorization header at all
  /// (Section 14.2: locked views carry no authenticated data).
  String? releaseToken() =>
      state.status == GateStatus.unlocked ? _releasedToken : null;

  /// Stops releasing immediately: drops the in-memory token and re-locks
  /// (Section 14.2 background/inactivity behavior).
  void lock() {
    _inactivityTimer?.cancel();
    _inactivityTimer = null;
    _releasedToken = null;
    if (state.status == GateStatus.unlocked ||
        state.status == GateStatus.locked) {
      state = AuthGateState(
        status: GateStatus.locked,
        availability: state.availability,
      );
    }
  }

  /// Resets the inactivity countdown — called from user interaction (the
  /// lock-gate wrapper listens for taps in the authenticated shell).
  void noteActivity() {
    if (state.status == GateStatus.unlocked) {
      _restartInactivityTimer();
    }
  }

  /// Persists a newly registered device token (MT-5.5-06 hands over the
  /// `POST /devices` response token). The value goes straight into secure
  /// storage and is NOT released: the gate lands locked until biometric
  /// success (Section 12.2; release contract).
  Future<void> storeToken(String token) async {
    await ref
        .read(secureTokenStoreProvider)
        .write(deviceTokenStorageKey, token);
    _releasedToken = null;
    _inactivityTimer?.cancel();
    _inactivityTimer = null;
    state = AuthGateState(
      status: GateStatus.locked,
      availability: await ref.read(biometricAuthProvider).availability(),
    );
  }

  /// Invalid, expired or revoked device credentials: discard the stored
  /// token and return to the onboarding/unlock flow (release contract,
  /// "Rejection and recovery") — never a silent edge-only fallback.
  Future<void> discardCredential() async {
    _inactivityTimer?.cancel();
    _inactivityTimer = null;
    _releasedToken = null;
    try {
      await ref.read(secureTokenStoreProvider).delete(deviceTokenStorageKey);
    } catch (_) {
      // Best effort — the gate still stops releasing either way.
    }
    state = const AuthGateState(status: GateStatus.noCredential);
    // Rejection returns the app to onboarding (release contract): the user
    // re-authenticates and registers again — no silent re-entry.
    ref.read(onboardingRequiredProvider.notifier).state = true;
  }

  /// Re-probes storage after [GateStatus.storageError] (lock view retry).
  Future<void> retryProbe() async {
    state = const AuthGateState(status: GateStatus.initializing);
    await _initialize();
  }

  void _restartInactivityTimer() {
    _inactivityTimer?.cancel();
    _inactivityTimer = Timer(ref.read(lockTimeoutProvider), lock);
  }
}

/// The single source of the gate state (Section 14.3: one provider graph).
final NotifierProvider<AuthGateNotifier, AuthGateState> authGateProvider =
    NotifierProvider<AuthGateNotifier, AuthGateState>(AuthGateNotifier.new);
